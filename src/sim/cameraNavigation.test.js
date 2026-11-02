import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_CAMERA_DISTANCE, DEFAULT_CAMERA_PITCH, DEFAULT_CAMERA_TARGET_HEIGHT,
  DEFAULT_CAMERA_YAW, getCameraPanDirection, getCameraPanTargetOffset,
} from './cameraNavigation.js';

test('default camera view is centered on the G1 robot', () => {
  assert.equal(DEFAULT_CAMERA_YAW, Math.PI / 2);
  assert.equal(DEFAULT_CAMERA_PITCH, 0.62);
  assert.equal(DEFAULT_CAMERA_DISTANCE, 7);
  assert.equal(DEFAULT_CAMERA_TARGET_HEIGHT, 0.8);
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
