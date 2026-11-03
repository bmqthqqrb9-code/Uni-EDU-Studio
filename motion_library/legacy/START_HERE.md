# LEGACY G1 EDU motion activities

These are teacher-reviewed starter **source examples**, not a hardware test report.
Each activity has a `robot.*` IDE script (`.py`), a structured block representation
(`.blocks.json`), and tightly cropped `*-blocks.png` and `*-ide.png` screenshots in
`images/`. These are screenshots of the actual app workspace/editor, captured by
`node tools/capture_motion_app_screenshots.mjs`. They show the running app's blocks
or IDE script, not a full-screen interface or a robot photograph.

## Use and safety

- The G1 computer (or a host with supported SDK/DDS access) must run the backend.
  Opening the browser app is not evidence that the robot is connected.
- Select the matching `legacy` controller mode, open an example from the
  Starter motion library, inspect it, and have a teacher explicitly approve every run.
- Do not run these examples automatically. Keep the supervised emergency-stop path available.
- The 180-degree in-place turn is approximate: it is a timed yaw-velocity command,
  not a closed-loop heading target. Clear the full turning area first.
- Gesture presets can continue after accepted by the vendor SDK; keep the arm area clear.
- Sensor activities require fresh, calibrated MID-360 front/rear distance data. If a
  sensor is missing or stale, the backend fails closed. These samples are not a
  replacement for supervised navigation or a commissioned Nav2 route.
- DUET physical execution requires its own compatible gateway, teacher authorization,
  required commissioning/acceptance, and explicit operator action. These files do
  not claim DUET is commissioned on any robot.
- DUET `walk(seconds)` keeps its bounded timed-velocity behavior; Legacy
  `robot.walk(steps)` is step-count based. Older DUET `forward(seconds)` programs
  remain accepted as an alias and are normalized to `walk` when edited.

No motion was run while creating or testing these files.
