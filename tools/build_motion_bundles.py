#!/usr/bin/env python3
"""Build the checked-in starter library and separate classroom motion ZIPs."""

from __future__ import annotations

import html
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "motion_library"
BUNDLES = ROOT / "deliverables"

LEGACY = [
    {
        "name": "walk-forward",
        "title": "Walk Forward",
        "description": "Get ready, then take two small forward steps.",
        "code": "robot.stand()\nrobot.wait(2)\nrobot.walk(2)",
    },
    {
        "name": "walk-backward",
        "title": "Walk Backward",
        "description": "Get ready, then take one small backward step.",
        "code": "robot.stand()\nrobot.wait(2)\nrobot.backward(1)",
    },
    {
        "name": "turn-around-180",
        "title": "Turn Around 180",
        "description": "Turn in place by about 180 degrees. The final angle is approximate.",
        "code": "robot.stand()\nrobot.wait(2)\nrobot.turn_around_180()",
    },
    {
        "name": "hands-up-gesture",
        "title": "Hands Up Gesture",
        "description": "Run a fixed, teacher-supervised G1 arm preset.",
        "code": 'robot.hold_arm("hands up", 2)',
    },
    {
        "name": "follow-along-walk-and-wave",
        "title": "Follow Along: Walk and Wave",
        "description": "Take one short walk, then perform a fixed hands-up gesture.",
        "code": 'robot.stand()\nrobot.wait(2)\nrobot.walk(1)\nrobot.hold_arm("hands up", 2)',
    },
    {
        "name": "follow-along-walk-turn-return",
        "title": "Follow Along: Walk, Turn, Return",
        "description": "Walk, make an approximate half-turn in place, then walk back.",
        "code": 'robot.stand()\nrobot.wait(2)\nrobot.walk(2)\nrobot.turn_around_180()\nrobot.backward(2)\nrobot.stand()',
    },
    {
        "name": "follow-along-classroom-groove",
        "title": "Follow Along: Classroom Groove",
        "description": "A short walk, a quarter turn, and a fixed clap preset.",
        "code": 'robot.stand()\nrobot.wait(2)\nrobot.walk(1)\nrobot.turn("left", 90)\nrobot.arm_action("clap")\nrobot.stand()',
    },
    {
        "name": "front-sensor-stop-or-go",
        "title": "Front Sensor: Stop or Go",
        "description": "Requires a fresh MID-360 front-distance sample; stand instead of walking when clearance is under one metre.",
        "code": "robot.stand()\nif robot.front_distance_m() < 1:\n    robot.stand()\nelse:\n    robot.walk(1)",
    },
    {
        "name": "rear-sensor-stop-or-go",
        "title": "Rear Sensor: Stop or Go",
        "description": "Requires a fresh MID-360 rear-distance sample; stand instead of backing up when clearance is under one metre.",
        "code": "robot.stand()\nif robot.rear_distance_m() < 1:\n    robot.stand()\nelse:\n    robot.backward(1)",
    },
]

DUET = [
    {
        "name": "walk-forward",
        "title": "Walk Forward",
        "description": "Take one short, conservative DUET forward motion.",
        "code": "duet.walk(1)",
    },
    {
        "name": "walk-backward",
        "title": "Walk Backward",
        "description": "Take one short, conservative DUET backward motion.",
        "code": "duet.backward(1)",
    },
    {
        "name": "turn-around-180",
        "title": "Turn Around 180",
        "description": "Turn in place by about 180 degrees using bounded yaw segments. The final angle is approximate.",
        "code": "duet.turn_around_180()",
    },
    {
        "name": "hands-up-gesture",
        "title": "Hands Up Gesture",
        "description": "Run the catalogued DUET hands-up gesture through the approved arm-target gateway.",
        "code": "duet.gesture_hands_up(1)",
    },
    {
        "name": "follow-along-walk-and-wave",
        "title": "Follow Along: Walk and Wave",
        "description": "Run a short forward motion and fixed hands-up gesture concurrently.",
        "code": "with duet.concurrent():\n    duet.walk(1)\n    duet.gesture_hands_up(1)",
    },
    {
        "name": "follow-along-walk-turn-return",
        "title": "Follow Along: Walk, Turn, Return",
        "description": "Walk, make an approximate half-turn in place, then walk back.",
        "code": "duet.walk(1)\nduet.turn_around_180()\nduet.backward(1)",
    },
    {
        "name": "follow-along-classroom-groove",
        "title": "Follow Along: Classroom Groove",
        "description": "A short walk, a timed left turn, and a fixed clap gesture.",
        "code": "duet.walk(1)\nduet.turn_left(1)\nduet.gesture_clap(1)",
    },
    {
        "name": "front-sensor-stop-or-go",
        "title": "Front Sensor: Stop or Go",
        "description": "Requires a fresh MID-360 front-distance sample; explicitly stop when clearance is under one metre.",
        "code": "if duet.front_distance_m() < 1:\n    duet.stop()\nelse:\n    duet.walk(1)",
    },
    {
        "name": "rear-sensor-stop-or-go",
        "title": "Rear Sensor: Stop or Go",
        "description": "Requires a fresh MID-360 rear-distance sample; explicitly stop when clearance is under one metre.",
        "code": "if duet.rear_distance_m() < 1:\n    duet.stop()\nelse:\n    duet.backward(1)",
    },
]

COLORS = {
    "control": ("#facc15", "#713f12"),
    "locomotion": ("#60a5fa", "#172554"),
    "gesture": ("#f9a8d4", "#831843"),
}
LABELS = {
    "stand": "Stand / ready",
    "wait": "Wait",
    "walk": "Walk forward",
    "backward": "Walk backward",
    "walk": "Walk forward",
    "turn": "Turn",
    "turn_left": "Turn left",
    "turn_around_180": "Turn around about 180° in place",
    "hold_arm": "Hold arm pose",
    "arm_action": "Run arm preset",
    "gesture_hands_up": "Hands up gesture",
    "gesture_clap": "Clap gesture",
    "stop": "Stop DUET motion",
}


def parse_blocks(code: str, prefix: str) -> list[dict]:
    lines = code.splitlines()
    block_prefix = "g1" if prefix == "robot" else prefix

    def parse(index: int, indent: int) -> tuple[list[dict], int]:
        nodes = []
        while index < len(lines):
            raw = lines[index]
            depth = len(raw) - len(raw.lstrip(" "))
            text = raw.strip()
            if not text:
                index += 1
                continue
            if depth < indent:
                break
            if depth > indent:
                raise ValueError(f"Unexpected indentation in {code!r} at line {index + 1}")
            condition = re.fullmatch(rf"if {prefix}\.(front|rear)_distance_m\(\) (<=|>=|==|!=|<|>) ([0-9.]+):", text)
            if condition:
                body, next_index = parse(index + 1, indent + 4)
                otherwise = []
                index = next_index
                if index < len(lines) and lines[index].strip() == "else:" and len(lines[index]) - len(lines[index].lstrip(" ")) == indent:
                    otherwise, index = parse(index + 1, indent + 4)
                nodes.append({
                    "type": "controls_if",
                    "sensor_block_type": f"{block_prefix}_{condition.group(1)}_distance_m",
                    "operator": condition.group(2),
                    "threshold": float(condition.group(3)),
                    "test": {
                        "type": "logic_compare",
                        "operator": condition.group(2),
                        "left": {"type": f"{block_prefix}_{condition.group(1)}_distance_m"},
                        "right": {"type": "math_number", "value": float(condition.group(3))},
                    },
                    "then": body,
                    "else": otherwise,
                })
                continue
            if text == "with duet.concurrent():":
                body, index = parse(index + 1, indent + 4)
                nodes.append({"type": "duet_concurrent_action", "blocks": body})
                continue
            if text == "else:":
                break
            call = re.fullmatch(rf"{prefix}\.([A-Za-z_]\w*)\((.*)\)", text)
            if not call:
                raise ValueError(f"Unsupported sample line: {text}")
            args = []
            raw_args = call.group(2).strip()
            if raw_args:
                # The curated examples use only quoted strings and plain literals.
                args = [arg.strip() for arg in re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', raw_args)]
            method = call.group(1)
            block_type = f"{block_prefix}_command_{method}"
            if prefix == "robot" and method == "arm_action" and args:
                action = args[0].strip('"\'').lower()
                suffix = re.sub(r"[^a-z0-9]+", "_", action).strip("_")
                block_type = f"g1_command_arm_action_{suffix}"
            nodes.append({
                "type": block_type,
                "method": method,
                "inputs": args,
            })
            index += 1
        return nodes, index

    blocks, _ = parse(0, 0)
    return blocks


def statement_lines(code: str) -> list[tuple[int, str]]:
    return [((len(line) - len(line.lstrip(" "))) // 4, line.strip()) for line in code.splitlines() if line.strip()]


def label_for_line(line: str, prefix: str) -> tuple[str, str]:
    if line == "with duet.concurrent():":
        return "control", "At the same time"
    if line.startswith("if "):
        condition = line[3:].removesuffix(":")
        return "control", f"If {condition}"
    if line == "else:":
        return "control", "Else"
    method_match = re.search(rf"{prefix}\.([A-Za-z_]\w*)\((.*)\)", line)
    if not method_match:
        return "control", line
    method, arguments = method_match.groups()
    display = LABELS.get(method, method.replace("_", " ").capitalize())
    arguments = arguments.strip()
    if method in {"walk", "backward", "forward", "turn_left", "turn_right", "wait", "gesture_hands_up", "gesture_clap"} and arguments:
        display += f" · {arguments}"
    elif method == "turn":
        display += f" · {arguments}"
    elif method in {"hold_arm", "arm_action"}:
        display += f" · {arguments}"
    category = "gesture" if any(word in method for word in ("arm", "gesture", "wave", "clap")) else "locomotion"
    return category, display


def svg_blocks(activity: dict, prefix: str) -> str:
    rows = []
    for level, line in statement_lines(activity["code"]):
        category, label = label_for_line(line, prefix)
        rows.append((level, category, label))
    line_height = 54
    max_level = max((row[0] for row in rows), default=0)
    width = max(480, min(980, 100 + max(len(label) for _, _, label in rows) * 9))
    height = 68 + max(1, len(rows)) * line_height + 28
    block_markup = []
    for index, (level, category, label) in enumerate(rows):
        y = 60 + index * line_height
        x = 26 + level * 34
        fill, text_color = COLORS[category]
        block_width = width - x - 24
        block_markup.append(
            f'<path d="M{x+7} {y} h{block_width-14} q7 0 7 7 v24 q0 7 -7 7 h-28 l-8 9 -8 -9 h-11 q-7 0 -7 -7 v-24 q0 -7 7 -7 z" '
            f'fill="{fill}" stroke="{text_color}" stroke-width="1.5"/>'
            f'<text x="{x+20}" y="{y+25}" font-family="Arial,sans-serif" font-size="16" font-weight="600" fill="{text_color}">{html.escape(label)}</text>'
        )
    markup = "".join(block_markup)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'<text x="24" y="24" font-family="Arial,sans-serif" font-size="11" font-weight="700" letter-spacing="1.1" fill="#475569">BLOCK EXAMPLE · GENERATED FROM BLOCK DATA · NOT AN APP SCREENSHOT</text>'
        f'{markup}</svg>\n'
    )


def wrap_code_line(line: str, max_chars: int = 92) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    indentation = len(line) - len(line.lstrip(" "))
    words = line[indentation:].split(" ")
    output = []
    current = " " * indentation
    for word in words:
        if len(current.rstrip()) + len(word) + 1 > max_chars and current.strip():
            output.append(current.rstrip())
            current = " " * (indentation + 4) + word
        else:
            current += ("" if current.endswith(" ") else " ") + word
    if current.strip():
        output.append(current.rstrip())
    return output


def svg_ide(activity: dict) -> str:
    lines = [wrapped for line in activity["code"].splitlines() for wrapped in wrap_code_line(line)]
    width = max(300, min(1120, 44 + max(len(line) for line in lines) * 9.7))
    line_height = 24
    top = 58
    height = top + max(1, len(lines)) * line_height + 18
    text = "".join(
        f'<text x="22" y="{top + index * line_height}" font-family="monospace" font-size="16" fill="#0f172a">{html.escape(line)}</text>'
        for index, line in enumerate(lines)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'<text x="22" y="26" font-family="Arial,sans-serif" font-size="11" font-weight="700" letter-spacing="1.1" fill="#475569">IDE SCRIPT · GENERATED CODE PREVIEW · NOT AN APP SCREENSHOT</text>'
        f'{text}</svg>\n'
    )


def write_bundle(version: str, prefix: str, activities: list[dict]) -> list[dict]:
    folder = OUTPUT / version
    images = folder / "images"
    folder.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)
    library_entries = []
    for activity in activities:
        name = activity["name"]
        code = activity["code"] + "\n"
        blocks = parse_blocks(activity["code"], prefix)
        (folder / f"{name}.py").write_text(code, encoding="utf-8")
        (folder / f"{name}.blocks.json").write_text(
            json.dumps(
                {
                    "format": "uni-edu-studio-block-example-v1",
                    "controller_version": version,
                    "name": name,
                    "title": activity["title"],
                    "blocks": blocks,
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        library_entries.append({
            "name": name,
            "title": activity["title"],
            "description": activity["description"],
            "code": code.rstrip(),
            "controller_version": version,
            "builtin": True,
        })

    readme = f"""# {version.upper()} G1 EDU motion activities

These are teacher-reviewed starter **source examples**, not a hardware test report.
Each activity has a `{prefix}.*` IDE script (`.py`), a structured block representation
(`.blocks.json`), and tightly cropped `*-blocks.png` and `*-ide.png` screenshots in
`images/`. These are screenshots of the actual app workspace/editor, captured by
`node tools/capture_motion_app_screenshots.mjs`. They show the running app's blocks
or IDE script, not a full-screen interface or a robot photograph.

## Use and safety

- The G1 computer (or a host with supported SDK/DDS access) must run the backend.
  Opening the browser app is not evidence that the robot is connected.
- Select the matching `{version}` controller mode, open an example from the
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
"""
    (folder / "START_HERE.md").write_text(readme, encoding="utf-8")
    (folder / "library.json").write_text(
        json.dumps(library_entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return library_entries


def create_zip(version: str) -> Path:
    source = OUTPUT / version
    BUNDLES.mkdir(parents=True, exist_ok=True)
    archive_path = BUNDLES / f"{version}-g1-edu-motion-activities.zip"
    activities = json.loads((source / "library.json").read_text(encoding="utf-8"))
    for activity in activities:
        for view in ("blocks", "ide"):
            screenshot = source / "images" / f"{activity['name']}-{view}.png"
            if not screenshot.is_file():
                raise FileNotFoundError(
                    f"Missing actual app screenshot {screenshot.relative_to(ROOT)}; "
                    "run tools/capture_motion_app_screenshots.mjs before building bundles."
                )
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, Path(version) / path.relative_to(source))
    return archive_path


def main() -> None:
    library = []
    library += write_bundle("legacy", "robot", LEGACY)
    library += write_bundle("duet", "duet", DUET)
    (OUTPUT / "library.json").write_text(
        json.dumps(library, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    archives = [create_zip("legacy"), create_zip("duet")]
    for archive in archives:
        print(f"Built {archive.relative_to(ROOT)} ({archive.stat().st_size} bytes)")
    print(f"Built {len(library)} named starter library activities.")


if __name__ == "__main__":
    main()
