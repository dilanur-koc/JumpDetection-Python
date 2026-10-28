"""Donanim gerektirmeyen mevcut davranis kontrolleri."""

import contextlib
import io
import unittest
from types import SimpleNamespace

from jump_detection.detector import reset, update
from jump_detection.features import govde_y_hesapla


class DetectorTests(unittest.TestCase):
    def setUp(self):
        self.durum = reset()
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def calibrate(self):
        for i in range(31):
            update(self.durum, i / 10, 0.5)
        self.assertEqual(self.durum["referans"], 0.5)

    def test_calibration_requires_enough_time(self):
        for i in range(10):
            result = update(self.durum, i / 10, 0.5)
        self.assertIsNone(self.durum["referans"])
        self.assertEqual(result[0], "CALIBRATING - STAND STILL")
        self.assertIsNone(result[2])

    def test_standing_still_calibrates_without_counting(self):
        self.calibrate()
        result = update(self.durum, 3.1, 0.5)
        self.assertEqual(result[0], "READY - JUMP!")
        self.assertEqual(self.durum["sayac"], 0)

    def test_fast_rise_counts_once_until_return(self):
        self.calibrate()
        result = update(self.durum, 3.1, 0.4)
        self.assertEqual(result[0], "JUMP DETECTED!")
        self.assertEqual(self.durum["sayac"], 1)
        self.assertFalse(self.durum["hazir"])
        update(self.durum, 3.2, 0.38)
        update(self.durum, 3.9, 0.4)
        self.assertEqual(self.durum["sayac"], 1)
        self.assertFalse(self.durum["hazir"])

    def test_return_before_cooldown_does_not_rearm(self):
        self.calibrate()
        update(self.durum, 3.1, 0.4)
        update(self.durum, 3.3, 0.5)
        self.assertFalse(self.durum["hazir"])
        update(self.durum, 3.8, 0.5)
        self.assertTrue(self.durum["hazir"])
        self.assertEqual(self.durum["sayac"], 1)

    def test_second_jump_after_return_and_new_history(self):
        self.calibrate()
        update(self.durum, 3.1, 0.4)
        for i in range(40, 46):
            update(self.durum, i / 10, 0.5)
        update(self.durum, 4.6, 0.4)
        self.assertEqual(self.durum["sayac"], 2)

    def test_slow_rise_does_not_count(self):
        self.calibrate()
        for i in range(1, 51):
            update(self.durum, 3.0 + i / 10, 0.5 - i * 0.002)
        self.assertEqual(self.durum["sayac"], 0)

    def test_fast_but_small_rise_does_not_count(self):
        self.calibrate()
        self.durum["gecmis"].clear()
        self.durum["gecmis"].append((3.0, 0.5))
        update(self.durum, 3.1, 0.46)
        self.assertEqual(self.durum["sayac"], 0)

    def test_first_sample_after_tracking_gap_has_no_speed(self):
        self.calibrate()
        self.durum["gecmis"].clear()
        result = update(self.durum, 10.0, 0.4)
        self.assertEqual(result[3], 0.0)
        self.assertEqual(self.durum["sayac"], 0)
        self.assertEqual(self.durum["referans"], 0.5)

    def test_reset_creates_independent_state(self):
        self.calibrate()
        update(self.durum, 3.1, 0.4)
        fresh = reset()
        self.assertEqual(fresh["sayac"], 0)
        self.assertIsNone(fresh["referans"])
        self.assertTrue(fresh["hazir"])
        self.assertEqual(len(fresh["gecmis"]), 0)
        self.assertEqual(self.durum["sayac"], 1)

    def test_torso_feature_averages_shoulders_and_hips(self):
        points = [SimpleNamespace(y=0.0) for _ in range(33)]
        for index, value in ((11, 0.2), (12, 0.4), (23, 0.6), (24, 0.8)):
            points[index].y = value
        self.assertAlmostEqual(govde_y_hesapla(points), 0.5)


if __name__ == "__main__":
    unittest.main()
