import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_CAMERA_DISTANCE, DEFAULT_CAMERA_PITCH, DEFAULT_CAMERA_TARGET_HEIGHT,
  DEFAULT_CAMERA_YAW, getCameraHorizontalFocusOffset, getCameraPanDirection, getCameraPanTargetOffset,
} from './cameraNavigation.js';

test('default camera view faces the G1 robot and frames it prominently', () => {
  assert.equal(DEFAULT_CAMERA_YAW, 0);
  assert.equal(DEFAULT_CAMERA_PITCH, 0.68);
  assert.equal(DEFAULT_CAMERA_DISTANCE, 9.5);
  assert.equal(DEFAULT_CAMERA_TARGET_HEIGHT, 0.8);
});

test('camera focus centers the robot in the unobstructed view area', () => {
  const offset = getCameraHorizontalFocusOffset(1280, 744, DEFAULT_CAMERA_DISTANCE, 1280 / 720);
  const horizontalHalfFov = Math.atan(Math.tan(42 * Math.PI / 360) * (1280 / 720));
  const projectedRobotX = 640 - (offset / (2 * DEFAULT_CAMERA_DISTANCE * Math.tan(horizontalHalfFov))) * 1280;

  assert.ok(offset > 0);
  assert.ok(Math.abs(projectedRobotX - 372) < 0.001);
  assert.equal(getCameraHorizontalFocusOffset(1280, 1280, DEFAULT_CAMERA_DISTANCE, 1280 / 720), 0);
  assert.equal(getCameraHorizontalFocusOffset(0, 744, DEFAULT_CAMERA_DISTANCE, 1280 / 720), 0);
});

test('keyboard directions match the camera keypad directions', () => {
  assert.deepEqual(getCameraPanDirection('ArrowUp'), [0, 1]);
  assert.deepEqual(getCameraPanDirection('w'), [0, 1]);
  assert.deepEqual(getCameraPanDirection('ArrowDown'), [0, -1]);
  assert.deepEqual(getCameraPanDirection('s'), [0, -1]);
  assert.deepEqual(getCameraPanDirection('ArrowLeft'), [-1, 0]);
  assert.deepEqual(getCameraPanDirection('ArrowRight'), [1, 0]);
  assert.equal(getCameraPanDirection('q'), null);
});

test('view up and down move the camera target in the intuitive screen direction', () => {
  assert.deepEqual(getCameraPanTargetOffset(0, 1, 1), { horizontal: 0, forward: -1 });
  assert.deepEqual(getCameraPanTargetOffset(0, -1, 1), { horizontal: 0, forward: 1 });
  assert.deepEqual(getCameraPanTargetOffset(1, 0, 1), { horizontal: 1, forward: -0 });
});
