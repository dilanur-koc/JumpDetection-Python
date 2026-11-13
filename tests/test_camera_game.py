"""Regressions for seated motion, one raised foot and lost camera tracking."""

import unittest
from dataclasses import replace
from types import SimpleNamespace

from jump_detection.game_detector import BodySample, CameraGameDetector, UpperBodySample


STANDING = BodySample(0.375, 0.85, 0.85, 0.15, True)
AIRBORNE = replace(STANDING, torso=0.335, left_ankle=0.81, right_ankle=0.81)


class CameraGameTests(unittest.TestCase):
    def calibrated(self):
        detector = CameraGameDetector()
        for i in range(15):
            self.assertFalse(detector.update(i * 0.08, STANDING))
        self.assertEqual(detector.status, "READY - JUMP")
        return detector

    def test_sitting_standing_and_one_raised_foot_do_not_trigger(self):
        detector = self.calibrated()
        seated = replace(STANDING, torso=0.49, standing=False)
        self.assertFalse(detector.update(1.20, seated))
        self.assertFalse(detector.update(1.28, STANDING))
        self.assertFalse(detector.update(1.36, replace(AIRBORNE, right_ankle=0.85)))
        self.assertEqual(detector.count, 0)

    def test_both_feet_and_torso_trigger_once_until_landing(self):
        detector = self.calibrated()
        self.assertTrue(detector.update(1.20, AIRBORNE))
        self.assertFalse(detector.update(1.28, AIRBORNE))
        for i in range(17, 23):
            self.assertFalse(detector.update(i * 0.08, STANDING))
        self.assertTrue(detector.update(1.84, AIRBORNE))
        self.assertEqual(detector.count, 2)

    def test_missing_pose_and_frame_gap_require_recalibration(self):
        for loss in ("pose", "gap"):
            with self.subTest(loss=loss):
                detector = self.calibrated()
                if loss == "pose":
                    detector.update(1.20, None)
                self.assertFalse(detector.update(1.60, AIRBORNE))
                self.assertIn("CALIBRATING", detector.status)
                self.assertEqual(detector.count, 0)

    def test_single_occluded_frame_keeps_reference_without_stale_velocity(self):
        detector = self.calibrated()
        self.assertFalse(detector.update(1.20, None))
        self.assertFalse(detector.update(1.28, AIRBORNE))
        self.assertEqual(detector.count, 0)
        self.assertFalse(detector.update(1.36, STANDING))
        self.assertTrue(detector.update(1.44, AIRBORNE))



class UpperBodyGameTests(unittest.TestCase):
    def sample(self, nose=0.33, left=0.45, right=0.45, width=0.24):
        points = [SimpleNamespace(x=0.5, y=1.2, visibility=0) for _ in range(33)]
        points[0] = SimpleNamespace(x=0.5, y=nose, visibility=1)
        points[11] = SimpleNamespace(x=0.5 - width / 2, y=left, visibility=1)
        points[12] = SimpleNamespace(x=0.5 + width / 2, y=right, visibility=1)
        self.assertIsNone(BodySample.from_landmarks(points))
        return UpperBodySample.from_landmarks(points, 4 / 3)

    def calibrated(self):
        detector = CameraGameDetector(upper_body=True)
        standing = self.sample()
        self.assertIsNotNone(standing)
        for i in range(15):
            self.assertFalse(detector.update(i * 0.08, standing))
        self.assertEqual(detector.status, "READY - JUMP")
        return detector

    def test_cropped_legs_allow_one_event_and_rearm_after_return(self):
        detector = self.calibrated()
        rise = self.sample(0.25, 0.37, 0.37)
        self.assertTrue(detector.update(1.20, rise))
        self.assertFalse(detector.update(1.28, rise))
        for i in range(17, 23):
            self.assertFalse(detector.update(i * 0.08, self.sample()))
        self.assertTrue(detector.update(1.84, rise))
        self.assertEqual(detector.count, 2)

    def test_nod_shrug_and_depth_shift_do_not_emit(self):
        cases = [self.sample(nose=0.25), self.sample(left=0.37),
                 self.sample(0.25, 0.37, 0.37, width=0.34)]
        for sample in cases:
            with self.subTest(sample=sample):
                detector = self.calibrated()
                self.assertFalse(detector.update(1.20, sample))
                self.assertEqual(detector.count, 0)
