# G1 EDU starter motion bundles

The app's **Starter motion library** is populated from `motion_library/library.json`.
Selecting **Load into editor** only changes the editor contents; it never connects to
the robot, submits a classroom queue item, or starts motion. Inspect the selected
controller version and program. Students still submit for teacher approval, and a
teacher must explicitly choose to run an approved program.

The ready-to-share ZIP deliverables are:

- `deliverables/legacy-g1-edu-motion-activities.zip`
- `deliverables/duet-g1-edu-motion-activities.zip`

Each package includes nine named activities: individual forward/backward locomotion,
an approximate in-place half-turn, a fixed gesture, follow-along combinations, and
front/rear sensor-gated activities. Every activity has an IDE script (`.py`), a
structured block representation (`.blocks.json`), and separate `*-blocks.png` and
`*-ide.png` screenshots. The PNGs are captured from the running app with Playwright
and tightly cropped to the actual Blockly workspace blocks or IDE editor. Filenames
use the same activity slug as the starter library. They are app screenshots, not
photos of a physical robot.

## Physical-host requirements and boundaries

- Physical control is through the Python backend on the G1 computer, or a supported
  host with Unitree SDK2 and DDS access. Browser reachability is not evidence of SDK
  connectivity. Follow [Environment and Host Setup](environment_and_host_setup.md).
- Legacy motion requires a successful SDK status probe. DUET motion additionally
  requires its configured gateway, authorization, commissioning/acceptance, and
  confirmed ownership.
- `robot.turn_around_180()` and `duet.turn_around_180()` are timed yaw-velocity
  motions. They aim for about 180 degrees in place but do not provide closed-loop
  heading accuracy. Keep the entire turn area clear and maintain teacher supervision.
- Front/rear sensor activities require fresh, calibrated MID-360 distance data. The
  backend rejects unavailable or stale samples. They are not autonomous navigation
  plans and do not replace commissioned Nav2 obstacle avoidance.
- Gestures use fixed vendor/catalog mappings. An accepted arm action may not be
  cancelable by the app; clear the arm workspace and keep the physical stop path
  available.

The bundles are examples, not evidence of hardware validation. No robot motion is
performed by the build or automated tests. Capture actual app screenshots and rebuild
the starter library and ZIPs with `node tools/capture_motion_app_screenshots.mjs`
while the app is running.

For the DUET-to-Legacy method-name mapping and the compatibility rationale, see
[DUET command naming audit](duet-legacy-command-naming.md).
