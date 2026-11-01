import assert from 'node:assert/strict';
import test from 'node:test';
import { compileDuetPoseFrames } from './duetVisionMotion.js';

function pose({
  leftWrist = [0.4, 0.05],
  rightWrist = [0.6, 0.05],
  visibility = 1,
} = {}) {
  const landmarks = Array.from({ length: 33 }, () => ({
    x: 0.5,
    y: 0.5,
    visibility,
  }));
  landmarks[11] = { x: 0.4, y: 0.3, visibility };
  landmarks[12] = { x: 0.6, y: 0.3, visibility };
  landmarks[13] = { x: 0.4, y: 0.42, visibility };
  landmarks[14] = { x: 0.6, y: 0.42, visibility };
  landmarks[15] = { x: leftWrist[0], y: leftWrist[1], visibility };
  landmarks[16] = { x: rightWrist[0], y: rightWrist[1], visibility };
  landmarks[23] = { x: 0.4, y: 0.75, visibility };
  landmarks[24] = { x: 0.6, y: 0.75, visibility };
  return landmarks;
}

test('vision pose mapping emits only bounded DUET catalog commands', () => {
  const result = compileDuetPoseFrames([
    { landmarks: pose({ leftWrist: [0.4, 0.05], rightWrist: [0.6, 0.95] }) },
  ]);
  assert.equal(result.code, 'duet.raise_left_arm("high", 1)');
  assert.match(result.summary, /approximate retarget/);
});

test('vision pose mapping detects a bilateral pose and a repeated wave', () => {
  const bilateral = compileDuetPoseFrames([
    { landmarks: pose() },
    { landmarks: pose() },
  ]);
  assert.equal(bilateral.code, 'duet.raise_both_arms("high", 1)');

  const waving = compileDuetPoseFrames([
    { landmarks: pose({ leftWrist: [0.35, 0.05], rightWrist: [0.6, 0.95] }) },
    { landmarks: pose({ leftWrist: [0.55, 0.05], rightWrist: [0.6, 0.95] }) },
    { landmarks: pose({ leftWrist: [0.35, 0.05], rightWrist: [0.6, 0.95] }) },
    { landmarks: pose({ leftWrist: [0.55, 0.05], rightWrist: [0.6, 0.95] }) },
  ]);
  assert.equal(waving.code, 'duet.wave_left("high", 1)');
});

test('vision pose mapping rejects empty and low-confidence observations', () => {
  assert.throws(() => compileDuetPoseFrames([]), /No video frames/);
  assert.throws(() => compileDuetPoseFrames([
    { landmarks: pose({ visibility: 0.1 }) },
  ]), /No clear arm movement/);
});
