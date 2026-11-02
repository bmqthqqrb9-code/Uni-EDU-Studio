export const DEFAULT_CAMERA_YAW = Math.PI / 2;
export const DEFAULT_CAMERA_PITCH = 0.62;
export const DEFAULT_CAMERA_DISTANCE = 7;
export const DEFAULT_CAMERA_TARGET_HEIGHT = 0.8;

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
