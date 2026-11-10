#!/usr/bin/env python3
"""Install a manually-started systemd user unit for the modified DUET controller."""

import argparse
import os
import re
import sys
from pathlib import Path


CONTROLLER_DIR = Path(__file__).resolve().parent
INTERFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")
CONTROL_DIR_SUFFIX = Path(".cache/uni-edu-duet")
SOCKET_PATH_LIMIT = 108


def validate_interface(interface: str, sysfs_root: Path = Path("/sys/class/net")) -> None:
    if (
        not INTERFACE_PATTERN.fullmatch(interface)
        or len(interface.encode("ascii", errors="ignore")) >= 16
        or not (sysfs_root / interface).is_dir()
    ):
        raise ValueError(
            f"{interface!r} is not a present Linux network interface; "
            "pass the G1 host's DDS interface with --interface."
        )


def render_unit(controller_dir: Path, home: Path, interface: str) -> str:
    controller_dir = controller_dir.resolve()
    home = home.resolve()
    executable = controller_dir / "build" / "g1_ctrl"
    control_dir = home / CONTROL_DIR_SUFFIX

    for value in (str(controller_dir), str(executable), str(control_dir)):
        if any(char in value for char in ('"', "\\", "%", "$")) or any(
            ord(char) < 32 or char.isspace() for char in value
        ):
            raise ValueError(
                "DUET source and home paths must not contain whitespace or systemd "
                'specifier characters (", \\, %, or $).'
            )
    if len(os.fsencode(control_dir / "controller.sock")) >= SOCKET_PATH_LIMIT:
        raise ValueError("DUET_CONTROL_DIR is too long for a Unix-domain socket path.")

    return f"""[Unit]
Description=Modified DUET G1 23-DOF controller (manual start only)
ConditionFileIsExecutable={executable}

[Service]
Type=simple
WorkingDirectory={controller_dir}
Environment=DUET_CONTROL_DIR={control_dir}
Environment=DUET_GATEWAY_ENABLED=true
UMask=0077
ExecStart={executable} --network {interface}
Restart=no
StandardOutput=journal
StandardError=journal
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install (but do not start or enable) the DUET G1 controller "
            "as a systemd user service."
        )
    )
    parser.add_argument(
        "--interface",
        required=True,
        help="present G1-host DDS network interface, as accepted by g1_ctrl --network",
    )
    args = parser.parse_args()

    if os.geteuid() == 0:
        parser.error("run this as the same non-root user that runs uni-edu-studio")
    try:
        validate_interface(args.interface)
        executable = CONTROLLER_DIR / "build" / "g1_ctrl"
        policy = (
            CONTROLLER_DIR
            / "config"
            / "policy"
            / "velocity"
            / "v0"
            / "exported"
            / "policy.onnx"
        )
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError(
                f"controller binary not found or not executable: {executable}; "
                "build deploy/robots/g1_23dof first."
            )
        if not policy.is_file():
            raise ValueError(f"configured DUET policy is missing: {policy}")

        home = Path.home().resolve()
        unit_dir = home / ".config" / "systemd" / "user"
        unit_path = unit_dir / "duet-g1-controller.service"
        unit_text = render_unit(CONTROLLER_DIR, home, args.interface)
        unit_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        if unit_path.exists():
            if unit_path.read_text(encoding="utf-8") == unit_text:
                print(f"DUET controller unit already matches: {unit_path}")
                print("No service was started or enabled.")
                return 0
            raise ValueError(
                f"{unit_path} already exists and differs; inspect it and move it "
                "aside before reinstalling."
            )
        descriptor = os.open(
            unit_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as unit_file:
            unit_file.write(unit_text)
    except (OSError, ValueError) as error:
        print(f"Could not install DUET controller unit: {error}", file=sys.stderr)
        return 1

    print(f"Installed {unit_path}")
    print(f"Controller and backend control directory: {home / CONTROL_DIR_SUFFIX}")
    print("The unit is not enabled or started. Review it, then run:")
    print("  systemctl --user daemon-reload")
    print("  systemctl --user start duet-g1-controller.service")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
