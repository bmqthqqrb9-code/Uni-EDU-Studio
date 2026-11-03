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
        self.assertEqual(len(entries), 18)
        for entry in entries:
            with self.subTest(version=entry["controller_version"], name=entry["name"]):
                if entry["controller_version"] == "legacy":
                    commands = g1_robot.parse_robot_program(entry["code"])
                else:
                    commands = duet_robot.parse_duet_program(entry["code"])
                self.assertTrue(commands)

    def test_each_activity_has_distinct_script_block_data_and_tightly_cropped_images(self):
        for version in ("legacy", "duet"):
            folder = ROOT / "motion_library" / version
            names = {path.stem for path in folder.glob("*.py")}
            self.assertEqual(len(names), 9)
            for name in names:
                self.assertTrue((folder / f"{name}.blocks.json").is_file())
                block_image = folder / "images" / f"{name}-blocks.svg"
                ide_image = folder / "images" / f"{name}-ide.svg"
                self.assertTrue(block_image.is_file())
                self.assertTrue(ide_image.is_file())
                self.assertIn("BLOCK EXAMPLE", block_image.read_text(encoding="utf-8"))
                self.assertIn("IDE SCRIPT", ide_image.read_text(encoding="utf-8"))
                self.assertIn("NOT AN APP SCREENSHOT", ide_image.read_text(encoding="utf-8"))
            self.assertIn(
                'width="300"',
                (folder / "images" / "turn-around-180-ide.svg").read_text(encoding="utf-8"),
            )

    def test_two_independent_zip_archives_contain_only_their_controller_examples(self):
        for version in ("legacy", "duet"):
            archive_path = ROOT / "deliverables" / f"{version}-g1-edu-motion-activities.zip"
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertTrue(names)
                self.assertTrue(all(path.startswith(f"{version}/") for path in names))
                self.assertIn(f"{version}/walk-forward.py", names)
                self.assertIn(f"{version}/walk-forward.blocks.json", names)
                self.assertIn(f"{version}/images/walk-forward-blocks.svg", names)
                self.assertIn(f"{version}/images/walk-forward-ide.svg", names)


if __name__ == "__main__":
    unittest.main()
