import unittest

try:
    from .safe_mode import (
        SAFE_MODE_ARM_INFLATION_METERS,
        _arm_model_envelopes,
        registered_arm_obstacle,
        registered_base_obstacle,
    )
    from .lidar_distance import DistanceSensorError
except ImportError:
    from safe_mode import (
        SAFE_MODE_ARM_INFLATION_METERS,
        _arm_model_envelopes,
        registered_arm_obstacle,
        registered_base_obstacle,
    )
    from lidar_distance import DistanceSensorError


def safety_snapshot(points, *, ready=True, pose=None):
    live_points = [
        {"x": point["x"], "y": point["y"]}
        for point in points
        if point["age_ms"] <= 1_500
    ]
    return {
        "ready": True,
        "localization": {
            "ready": True,
            "frame_id": "map",
            "pose": pose or {"x": 0.0, "y": 0.0, "z": 0.0, "yaw_rad": 0.0},
        },
        "registeredObstacles": {
            "ready": ready,
            "frame_id": "map",
            "age_ms": 50 if ready else 2_000,
            "points": points,
        },
        "liveObstacles": {
            "ready": True,
            "frame_id": "map",
            "age_ms": 50,
            "points": live_points,
        },
    }


class RegisteredSafeModeTests(unittest.TestCase):
    def test_swept_path_stops_for_obstacle_on_sideways_motion(self):
        snapshot = safety_snapshot([{"x": 0.0, "y": 0.4, "z": 0.0, "age_ms": 20}])

        result = registered_base_obstacle(snapshot, 0.0, 0.2, 0.0, 1.0, margin_m=0.0)

        self.assertIsNotNone(result)
        self.assertIn("overlaps", result["reason"])

    def test_stale_observation_only_blocks_when_it_overlaps_current_swept_path(self):
        relevant = safety_snapshot([{"x": 0.0, "y": 0.0, "z": 0.0, "age_ms": 1_700}])
        irrelevant = safety_snapshot([{"x": 40.0, "y": 40.0, "z": 0.0, "age_ms": 1_700}])

        self.assertIn(
            "stale",
            registered_base_obstacle(relevant, 0.2, 0.0, 0.0, 0.1, margin_m=0.0)["reason"],
        )
        self.assertIsNone(
            registered_base_obstacle(irrelevant, 0.2, 0.0, 0.0, 0.1, margin_m=0.0)
        )

    def test_missing_registered_coverage_fails_closed(self):
        snapshot = safety_snapshot([], ready=False)

        with self.assertRaisesRegex(DistanceSensorError, "stale"):
            registered_base_obstacle(snapshot, 0.2, 0.0, 0.0, 0.2)

    def test_registered_history_blocks_obstacles_without_live_costmap_points(self):
        snapshot = safety_snapshot([
            {"x": 0.0, "y": 0.4, "z": 0.0, "age_ms": 800}
        ])
        snapshot["liveObstacles"] = {
            "ready": False,
            "frame_id": "map",
            "age_ms": None,
            "points": [],
        }

        result = registered_base_obstacle(
            snapshot, 0.0, 0.2, 0.0, 1.0, margin_m=0.0
        )

        self.assertIsNotNone(result)

    def test_arm_envelope_uses_model_reach_and_requested_inflation(self):
        envelopes = _arm_model_envelopes()
        self.assertEqual(len(envelopes), 2)
        self.assertGreater(envelopes[0]["radius"], SAFE_MODE_ARM_INFLATION_METERS)
        self.assertAlmostEqual(envelopes[0]["y"], -envelopes[1]["y"], places=4)

        envelope = envelopes[0]
        snapshot = safety_snapshot([{
            "x": envelope["x"] + envelope["radius"] - 0.01,
            "y": envelope["y"],
            "z": envelope["z"],
            "age_ms": 20,
        }])
        self.assertIsNotNone(registered_arm_obstacle(snapshot))

    def test_arm_envelope_requires_height_and_fresh_coverage(self):
        snapshot = safety_snapshot([], pose={"x": 0.0, "y": 0.0, "yaw_rad": 0.0})

        with self.assertRaisesRegex(DistanceSensorError, "height"):
            registered_arm_obstacle(snapshot)


if __name__ == "__main__":
    unittest.main()
