from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET
from functools import lru_cache
from typing import Any

try:
    from .lidar_distance import DistanceSensorError
except ImportError:
    from lidar_distance import DistanceSensorError

SAFE_MODE_STOP_MARGIN_METERS = 1.0
SAFE_MODE_ARM_INFLATION_METERS = 0.2
REGISTERED_OBSTACLE_MAX_AGE_MS = 1_500
REGISTERED_OBSTACLE_MAX_POINTS = 5_000
BASE_FOOTPRINT = {"front": 0.175, "rear": 0.175, "half_width": 0.225}
_DUET_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "vendor",
    "DUET",
    "src",
    "assets",
    "robots",
    "unitree_g1",
    "xmls",
    "g1_23dof.xml",
)


def footprint_clearance(sample: dict[str, Any]) -> float:
    if not isinstance(sample, dict):
        raise DistanceSensorError("MID-360 footprint sample is invalid.")
    if sample.get("clear") is True:
        clearance = sample.get("max_range_m")
    else:
        clearance = sample.get("distance_m")
    if (
        isinstance(clearance, bool)
        or not isinstance(clearance, (int, float))
        or not math.isfinite(float(clearance))
        or float(clearance) < 0
    ):
        raise DistanceSensorError("MID-360 footprint sample has no valid clearance.")
    return float(clearance)


def obstacle_within_margin(sample: dict[str, Any], margin_m: float = SAFE_MODE_STOP_MARGIN_METERS) -> bool:
    return footprint_clearance(sample) < margin_m


def current_navigation_safety_snapshot() -> dict[str, Any]:
    try:
        from .navigation_bridge import navigation_safety_snapshot
    except ImportError:
        from navigation_bridge import navigation_safety_snapshot
    snapshot = navigation_safety_snapshot()
    if not isinstance(snapshot, dict) or snapshot.get("ready") is not True:
        detail = snapshot.get("error") if isinstance(snapshot, dict) else None
        raise DistanceSensorError(
            detail if isinstance(detail, str) and detail else "Registered obstacle sensing is unavailable."
        )
    return snapshot


@lru_cache(maxsize=4)
def _arm_model_envelopes(model_path: str = _DUET_MODEL_PATH) -> tuple[dict[str, float], ...]:
    try:
        root = ET.parse(model_path).getroot()
    except (OSError, ET.ParseError) as error:
        raise DistanceSensorError(f"G1 arm collision model is unavailable: {error}") from error
    worldbody = root.find("worldbody")
    if worldbody is None:
        raise DistanceSensorError("G1 arm collision model has no worldbody.")
    torso = next((body for body in worldbody.iter("body") if body.get("name") == "torso_link"), None)
    if torso is None:
        raise DistanceSensorError("G1 arm collision model has no torso link.")
    torso_position = _model_vector(torso.get("pos"), (0.0, 0.0, 0.0))
    envelopes = []
    for side, sign in (("left", 1.0), ("right", -1.0)):
        shoulder = next(
            (body for body in torso.findall("body") if body.get("name") == f"{side}_shoulder_pitch_link"),
            None,
        )
        if shoulder is None:
            raise DistanceSensorError(f"G1 arm collision model is missing the {side} shoulder.")
        shoulder_position = _model_vector(shoulder.get("pos"), (0.0, 0.0, 0.0))
        chain_length = 0.0
        maximum_collision_extent = 0.0
        current = shoulder
        while current is not None:
            if current is not shoulder:
                body_position = _model_vector(current.get("pos"), (0.0, 0.0, 0.0))
                chain_length += math.sqrt(sum(value * value for value in body_position))
            for geom in current.findall("geom"):
                if geom.get("class") != "collision":
                    continue
                size = _model_vector(geom.get("size"), ())
                if not size:
                    continue
                fromto = _model_vector(geom.get("fromto"), ())
                extent = max(size)
                if len(fromto) == 6:
                    segment = math.sqrt(sum(
                        (fromto[index + 3] - fromto[index]) ** 2
                        for index in range(3)
                    ))
                    extent += segment / 2
                maximum_collision_extent = max(maximum_collision_extent, extent)
            children = current.findall("body")
            current = children[0] if children else None
        envelopes.append({
            "x": torso_position[0] + shoulder_position[0],
            "y": torso_position[1] + sign * abs(shoulder_position[1]),
            "z": torso_position[2] + shoulder_position[2],
            "radius": chain_length + maximum_collision_extent + SAFE_MODE_ARM_INFLATION_METERS,
        })
    return tuple(envelopes)


def _model_vector(value: str | None, fallback: tuple[float, ...]) -> tuple[float, ...]:
    if value is None:
        return fallback
    try:
        result = tuple(float(part) for part in value.split())
    except ValueError as error:
        raise DistanceSensorError("G1 arm collision model contains a non-numeric vector.") from error
    if not result or not all(math.isfinite(part) for part in result):
        raise DistanceSensorError("G1 arm collision model contains an invalid vector.")
    return result


def _registered_snapshot_points(snapshot: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(snapshot, dict) or snapshot.get("ready") is not True:
        detail = snapshot.get("error") if isinstance(snapshot, dict) else None
        raise DistanceSensorError(
            detail if isinstance(detail, str) and detail else "Registered obstacle sensing is unavailable."
        )
    localization = snapshot.get("localization")
    obstacles = snapshot.get("registeredObstacles")
    if (
        not isinstance(localization, dict)
        or localization.get("ready") is not True
        or not isinstance(obstacles, dict)
        or obstacles.get("ready") is not True
        or obstacles.get("frame_id") != localization.get("frame_id")
    ):
        raise DistanceSensorError("Registered obstacle data is stale or not aligned to localization.")
    pose = localization.get("pose")
    points = obstacles.get("points")
    if not isinstance(pose, dict) or not isinstance(points, list) or len(points) > REGISTERED_OBSTACLE_MAX_POINTS:
        raise DistanceSensorError("Registered obstacle snapshot has an invalid shape.")
    required_pose = ("x", "y", "yaw_rad")
    if any(
        isinstance(pose.get(axis), bool)
        or not isinstance(pose.get(axis), (int, float))
        or not math.isfinite(float(pose[axis]))
        for axis in required_pose
    ):
        raise DistanceSensorError("Registered obstacle localization is invalid.")
    return pose, points


def registered_base_obstacle(
    snapshot: dict[str, Any],
    vx_mps: float,
    vy_mps: float,
    vyaw_rps: float,
    horizon_s: float,
    margin_m: float = SAFE_MODE_STOP_MARGIN_METERS,
) -> dict[str, Any] | None:
    pose, points = _registered_snapshot_points(snapshot)
    values = (vx_mps, vy_mps, vyaw_rps, horizon_s, margin_m)
    if not all(math.isfinite(float(value)) for value in values) or horizon_s < 0 or margin_m < 0:
        raise DistanceSensorError("Safe Mode swept-path parameters are invalid.")
    steps = max(1, math.ceil(horizon_s / 0.1))
    step_seconds = horizon_s / steps if horizon_s else 0.0
    x, y, yaw = (float(pose[axis]) for axis in ("x", "y", "yaw_rad"))
    for step in range(steps + 1):
        if step:
            cosine = math.cos(yaw)
            sine = math.sin(yaw)
            x += (vx_mps * cosine - vy_mps * sine) * step_seconds
            y += (vx_mps * sine + vy_mps * cosine) * step_seconds
            yaw += vyaw_rps * step_seconds
        cosine = math.cos(yaw)
        sine = math.sin(yaw)
        for point in points:
            age = point.get("age_ms")
            px, py = point.get("x"), point.get("y")
            if (
                isinstance(age, bool)
                or not isinstance(age, (int, float))
                or not math.isfinite(float(age))
                or isinstance(px, bool)
                or not isinstance(px, (int, float))
                or isinstance(py, bool)
                or not isinstance(py, (int, float))
                or not math.isfinite(float(px))
                or not math.isfinite(float(py))
            ):
                raise DistanceSensorError("Registered obstacle point is invalid.")
            dx, dy = float(px) - x, float(py) - y
            robot_x = cosine * dx + sine * dy
            robot_y = -sine * dx + cosine * dy
            inside = (
                -BASE_FOOTPRINT["rear"] - margin_m <= robot_x <= BASE_FOOTPRINT["front"] + margin_m
                and abs(robot_y) <= BASE_FOOTPRINT["half_width"] + margin_m
            )
            if inside:
                if age > REGISTERED_OBSTACLE_MAX_AGE_MS:
                    return {
                        "reason": "A stale obstacle observation overlaps the planned robot footprint.",
                        "distance_m": math.hypot(dx, dy),
                        "age_ms": round(float(age)),
                    }
                return {
                    "reason": "A registered obstacle overlaps the planned robot footprint.",
                    "distance_m": math.hypot(dx, dy),
                    "age_ms": round(float(age)),
                }
    return None


def registered_arm_obstacle(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    pose, points = _registered_snapshot_points(snapshot)
    if (
        isinstance(pose.get("z"), bool)
        or not isinstance(pose.get("z"), (int, float))
        or not math.isfinite(float(pose["z"]))
    ):
        raise DistanceSensorError("Robot height is unavailable for arm-envelope checking.")
    envelopes = _arm_model_envelopes()
    cosine = math.cos(float(pose["yaw_rad"]))
    sine = math.sin(float(pose["yaw_rad"]))
    for envelope in envelopes:
        shoulder_x = float(pose["x"]) + envelope["x"] * cosine - envelope["y"] * sine
        shoulder_y = float(pose["y"]) + envelope["x"] * sine + envelope["y"] * cosine
        shoulder_z = float(pose["z"]) + envelope["z"]
        for point in points:
            x, y, z, age = (
                point.get("x"), point.get("y"), point.get("z"), point.get("age_ms")
            )
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in (x, y, z, age)
            ):
                raise DistanceSensorError("Registered 3D obstacle point is invalid.")
            distance = math.sqrt(
                (float(x) - shoulder_x) ** 2
                + (float(y) - shoulder_y) ** 2
                + (float(z) - shoulder_z) ** 2
            )
            if distance <= envelope["radius"]:
                return {
                    "reason": (
                        "A registered obstacle intersects the model-derived arm envelope "
                        f"inflated by {SAFE_MODE_ARM_INFLATION_METERS:.2f} m."
                        if age <= REGISTERED_OBSTACLE_MAX_AGE_MS
                        else "A stale obstacle observation overlaps the model-derived arm envelope."
                    ),
                    "distance_m": distance,
                    "age_ms": round(float(age)),
                    "arm_radius_m": envelope["radius"],
                }
    return None
