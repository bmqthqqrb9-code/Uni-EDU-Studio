export const DEFAULT_CAMERA_YAW = 0;
export const DEFAULT_CAMERA_PITCH = 0.68;
export const DEFAULT_CAMERA_DISTANCE = 9.5;
export const DEFAULT_CAMERA_TARGET_HEIGHT = 0.8;

export function getCameraHorizontalFocusOffset(viewportWidth, visibleWidth, distance, aspect, verticalFovDegrees = 42) {
  if (![viewportWidth, visibleWidth, distance, aspect, verticalFovDegrees].every(Number.isFinite)
    || viewportWidth <= 0
    || distance <= 0
    || aspect <= 0) {
    return 0;
  }
  const visibleViewportWidth = Math.max(0, Math.min(viewportWidth, visibleWidth));
  const centerDifference = (viewportWidth - visibleViewportWidth) / 2;
  const verticalHalfFov = verticalFovDegrees * Math.PI / 360;
  const horizontalHalfFov = Math.atan(Math.tan(verticalHalfFov) * aspect);
  return centerDifference / viewportWidth * 2 * distance * Math.tan(horizontalHalfFov);
}

export function getCameraPanDirection(key) {
  switch (key.toLowerCase()) {
    case 'arrowleft':
    case 'a':
      return [-1, 0];
    case 'arrowright':
    case 'd':
      return [1, 0];
    case 'arrowup':
    case 'w':
      return [0, 1];
    case 'arrowdown':
    case 's':
      return [0, -1];
    default:
      return null;
  }
}

export function getCameraPanTargetOffset(horizontal, vertical, step) {
  return {
    horizontal: horizontal * step,
    forward: -vertical * step,
  };
}
