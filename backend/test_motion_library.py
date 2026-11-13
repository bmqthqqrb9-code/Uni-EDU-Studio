import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import duet_robot
import g1_robot


class StarterMotionLibraryTests(unittest.TestCase):
    def test_examples_are_validated_without_executing_motion(self):
        entries = json.loads((ROOT / "motion_library" / "library.json").read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 24)
        for entry in entries:
            with self.subTest(version=entry["controller_version"], name=entry["name"]):
                if entry["controller_version"] == "legacy":
                    commands = g1_robot.parse_robot_program(entry["code"])
                else:
                    commands = duet_robot.parse_duet_program(entry["code"])
                self.assertTrue(commands)

    def test_legacy_reference_sequences_are_in_the_starter_library_in_order(self):
        entries = json.loads((ROOT / "motion_library" / "legacy" / "library.json").read_text(encoding="utf-8"))
        by_name = {entry["name"]: entry["code"] for entry in entries}
        expected = {
            "walk-forward": "robot.stand()\nrobot.wait(2)\nrobot.walk(2)",
            "walk-backward": "robot.stand()\nrobot.wait(2)\nrobot.backward(2)",
            "turn-around-180": "robot.stand()\nrobot.wait(2)\nrobot.turn_around_180()",
            "turn-left-90": 'robot.stand()\nrobot.wait(2)\nrobot.turn("left", 90)',
            "sidestep-right": 'robot.stand()\nrobot.wait(2)\nrobot.sidestep("right", 2)',
            "hands-up-gesture": 'robot.stand()\nrobot.wait(2)\nrobot.arm_action("hands up")',
            "walk-backward-then-clap": 'robot.stand()\nrobot.backward(2)\nrobot.wait(2)\nrobot.arm_action("clap")\nrobot.wait(2)',
            "high-five-turn-around-walk-forward": 'robot.stand()\nrobot.arm_action("high five")\nrobot.wait(2)\nrobot.turn_around_180()\nrobot.walk(2)',
            "walk-forward-turn-around-walk-back": "robot.stand()\nrobot.wait(2)\nrobot.walk(2)\nrobot.turn_around_180()\nrobot.backward(2)\nrobot.stand()",
            "walk-in-a-square-looped": 'robot.stand()\nfor _ in range(4):\n    robot.walk(2)\n    robot.turn("left", 90)\n    robot.wait(2)',
        }
        for name, code in expected.items():
            with self.subTest(name=name):
                self.assertEqual(by_name[name], code)

        square_blocks = json.loads(
            (ROOT / "motion_library" / "legacy" / "walk-in-a-square-looped.blocks.json").read_text(
                encoding="utf-8"
            )
        )["blocks"]
        self.assertEqual(square_blocks[1]["type"], "controls_repeat_ext")
        self.assertEqual(square_blocks[1]["times"], 4)
        self.assertEqual(
            [block["method"] for block in square_blocks[1]["body"]],
            ["walk", "turn", "wait"],
        )

        loop_commands = g1_robot.parse_robot_program(by_name["walk-in-a-square-looped"])
        self.assertEqual(
            [command["method"] for command in loop_commands],
            [
                "stand", "walk", "turn", "wait", "walk", "turn", "wait",
                "walk", "turn", "wait", "walk", "turn", "wait",
            ],
        )

    def test_each_activity_has_distinct_script_block_data_and_screenshots(self):
        for version in ("legacy", "duet"):
            folder = ROOT / "motion_library" / version
            names = {path.stem for path in folder.glob("*.py")}
            self.assertEqual(len(names), 15 if version == "legacy" else 9)
            for name in names:
                self.assertTrue((folder / f"{name}.blocks.json").is_file())
                for view in ("blocks", "ide"):
                    image = folder / "images" / f"{name}-{view}.png"
                    self.assertTrue(image.is_file())
                    self.assertTrue(image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_two_independent_zip_archives_contain_only_their_controller_examples(self):
        for version in ("legacy", "duet"):
            archive_path = ROOT / "deliverables" / f"{version}-g1-edu-motion-activities.zip"
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertTrue(names)
                self.assertTrue(all(path.startswith(f"{version}/") for path in names))
                self.assertIn(f"{version}/walk-forward.py", names)
                self.assertIn(f"{version}/walk-forward.blocks.json", names)
                self.assertIn(f"{version}/images/walk-forward-blocks.png", names)
                self.assertIn(f"{version}/images/walk-forward-ide.png", names)
                self.assertEqual(
                    sum(path.endswith(".py") for path in names if path.startswith(f"{version}/")),
                    15 if version == "legacy" else 9,
                )


if __name__ == "__main__":
    unittest.main()
