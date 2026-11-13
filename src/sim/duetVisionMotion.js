const VISION_WASM_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.2.0/wasm';
const POSE_MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';
const MAX_VIDEO_SECONDS = 30;
const VIDEO_SAMPLE_INTERVAL_MS = 500;
const MIN_LANDMARK_VISIBILITY = 0.55;

let poseLandmarkerPromise;

export async function getDuetPoseLandmarker() {
  if (!poseLandmarkerPromise) {
    poseLandmarkerPromise = import('@mediapipe/tasks-vision')
      .then(({ FilesetResolver, PoseLandmarker }) => (
        FilesetResolver.forVisionTasks(VISION_WASM_BASE)
          .then((fileset) => PoseLandmarker.createFromOptions(fileset, {
            baseOptions: { modelAssetPath: POSE_MODEL_URL },
            runningMode: 'VIDEO',
            numPoses: 1,
          }))
      ))
      .catch((error) => {
        poseLandmarkerPromise = null;
        throw new Error(`Local pose estimation could not start: ${error.message}`);
      });
  }
  return poseLandmarkerPromise;
}

function visible(landmark) {
  return landmark
    && Number.isFinite(landmark.x)
    && Number.isFinite(landmark.y)
    && Number(landmark.visibility ?? 1) >= MIN_LANDMARK_VISIBILITY;
}

function armLevel(landmarks, side) {
  const indexes = side === 'left'
    ? { shoulder: 11, elbow: 13, wrist: 15, hip: 23 }
    : { shoulder: 12, elbow: 14, wrist: 16, hip: 24 };
  const shoulder = landmarks[indexes.shoulder];
  const elbow = landmarks[indexes.elbow];
  const wrist = landmarks[indexes.wrist];
  const hip = landmarks[indexes.hip];
  if (![shoulder, elbow, wrist, hip].every(visible)) return null;

  const torsoLength = Math.hypot(shoulder.x - hip.x, shoulder.y - hip.y);
  if (torsoLength < 0.05) return null;
  const lift = (shoulder.y - wrist.y) / torsoLength;
  if (lift >= 0.55) return 'high';
  if (lift >= 0.1) return 'mid';
  if (lift >= -0.45 && wrist.y < hip.y) return 'low';
  return null;
}

function frameAction(landmarks, history) {
  const left = armLevel(landmarks, 'left');
  const right = armLevel(landmarks, 'right');
  const leftWrist = landmarks[15];
  const rightWrist = landmarks[16];
  if (visible(leftWrist)) history.left.push(leftWrist.x);
  if (visible(rightWrist)) history.right.push(rightWrist.x);
  for (const values of Object.values(history)) {
    if (values.length > 6) values.shift();
  }

  const isWave = (side, level) => {
    const values = history[side];
    return (level === 'mid' || level === 'high')
      && values.length >= 4
      && Math.max(...values) - Math.min(...values) >= 0.12;
  };
  if (left && right && left === right) {
    return [{ key: `raise_both_arms:${left}`, code: `duet.raise_both_arms("${left}", 1)` }];
  }
  const actions = [];
  if (left) {
    const waving = isWave('left', left);
    actions.push({
      key: `${waving ? 'wave_left' : 'raise_left_arm'}:${left}`,
      code: `duet.${waving ? 'wave_left' : 'raise_left_arm'}("${left}", 1)`,
    });
  }
  if (right) {
    const waving = isWave('right', right);
    actions.push({
      key: `${waving ? 'wave_right' : 'raise_right_arm'}:${right}`,
      code: `duet.${waving ? 'wave_right' : 'raise_right_arm'}("${right}", 1)`,
    });
  }
  return actions.length ? actions : [{ key: 'carry', code: 'duet.reset_arms()' }];
}

export function compileDuetPoseFrames(frames) {
  if (!Array.isArray(frames) || !frames.length) {
    throw new Error('No video frames were available for pose analysis.');
  }
  const history = { left: [], right: [] };
  const actions = [];
  frames.forEach((frame) => {
    const landmarks = frame?.landmarks;
    if (!Array.isArray(landmarks)) return;
    frameAction(landmarks, history).forEach((action) => {
      const previous = actions.at(-1);
      const waveStartKey = action.key.startsWith('wave_left:')
        ? `raise_left_arm:${action.key.split(':')[1]}`
        : action.key.startsWith('wave_right:')
          ? `raise_right_arm:${action.key.split(':')[1]}`
          : null;
      if (waveStartKey && previous?.key === waveStartKey) actions[actions.length - 1] = action;
      else if (previous?.key !== action.key) actions.push(action);
    });
  });
  const filtered = actions.filter((action, index) => (
    action.key !== 'carry' || index > 0 && index < actions.length - 1
  ));
  if (!filtered.length) {
    throw new Error('No clear arm movement was detected. Use a well-lit, front-facing view with both shoulders and wrists visible.');
  }
  const code = filtered.map(({ code }) => code).join('\n');
  return {
    code,
    actionCount: filtered.length,
    summary: `Mapped ${filtered.length} observed arm pose change${filtered.length === 1 ? '' : 's'} to approved DUET commands. This is an approximate retarget, not exact motion copying.`,
  };
}

function seekTo(video, timeSeconds) {
  if (Math.abs(video.currentTime - timeSeconds) < 0.001) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const finish = () => {
      video.removeEventListener('seeked', finish);
      video.removeEventListener('error', fail);
      resolve();
    };
    const fail = () => {
      video.removeEventListener('seeked', finish);
      video.removeEventListener('error', fail);
      reject(new Error('The selected video could not be decoded.'));
    };
    video.addEventListener('seeked', finish, { once: true });
    video.addEventListener('error', fail, { once: true });
    video.currentTime = timeSeconds;
  });
}

export async function analyzeDuetVideo(video, onProgress = () => {}) {
  if (
    typeof HTMLVideoElement === 'undefined'
    || !(video instanceof HTMLVideoElement)
    || !Number.isFinite(video.duration)
    || video.duration <= 0
  ) {
    throw new Error('Choose a playable video before analyzing motion.');
  }
  if (video.duration > MAX_VIDEO_SECONDS) {
    throw new Error(`Vision motion clips must be ${MAX_VIDEO_SECONDS} seconds or shorter.`);
  }
  if (video.videoWidth < 1 || video.videoHeight < 1) {
    throw new Error('Wait for the video preview to load before analyzing it.');
  }
  const originalTime = video.currentTime;
  const landmarker = await getDuetPoseLandmarker();
  const frames = [];
  const sampleCount = Math.ceil((video.duration * 1000) / VIDEO_SAMPLE_INTERVAL_MS) + 1;
  try {
    let sampleIndex = 0;
    for (let timestampMs = 0; timestampMs <= video.duration * 1000; timestampMs += VIDEO_SAMPLE_INTERVAL_MS) {
      await seekTo(video, Math.min(timestampMs / 1000, video.duration));
      const result = landmarker.detectForVideo(video, timestampMs + 1);
      if (result.landmarks?.[0]) frames.push({ landmarks: result.landmarks[0] });
      sampleIndex += 1;
      onProgress(Math.min(1, sampleIndex / sampleCount));
    }
  } finally {
    await seekTo(video, Math.min(originalTime, video.duration));
  }
  return compileDuetPoseFrames(frames);
}

export async function captureDuetLiveMotion(source, durationSeconds = 5, onProgress = () => {}) {
  const width = source?.videoWidth || source?.width || 0;
  const height = source?.videoHeight || source?.height || 0;
  if (!source || width < 1 || height < 1) {
    throw new Error('Start or select a live camera source before capturing motion.');
  }
  if (!Number.isFinite(durationSeconds) || durationSeconds < 2 || durationSeconds > 10) {
    throw new Error('Live motion capture must be between 2 and 10 seconds.');
  }
  const landmarker = await getDuetPoseLandmarker();
  const frames = [];
  const startedAt = performance.now();
  let timestampMs = 0;
  const intervalMs = VIDEO_SAMPLE_INTERVAL_MS;
  while (performance.now() - startedAt < durationSeconds * 1000) {
    timestampMs = Math.max(timestampMs + 1, Math.round(performance.now() - startedAt));
    const result = landmarker.detectForVideo(source, timestampMs);
    if (result.landmarks?.[0]) frames.push({ landmarks: result.landmarks[0] });
    const progress = Math.min(1, (performance.now() - startedAt) / (durationSeconds * 1000));
    onProgress(progress);
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs));
  }
  return compileDuetPoseFrames(frames);
}
