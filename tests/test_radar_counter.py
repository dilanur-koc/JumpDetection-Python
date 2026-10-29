"""Sentetik durum makinasi testleri; fiziksel ziplama dogrulamasi degildir."""

from dataclasses import asdict
import unittest

from radar.counter import CounterSettings, ExperimentalCounter
from radar.protocol import Target


def target(x=0, speed=0, slot=1):
    return Target(slot, True, x, 1000, speed, 320)


class RadarCounterTests(unittest.TestCase):
    def setUp(self):
        self.counter = ExperimentalCounter()

    def calibrate(self, start=0.0, x=0):
        for tick in range(12):
            self.counter.update(start + tick / 10, [target(x)])
        self.assertTrue(self.counter.ready)

    def burst(self, start=1.2, x=0):
        events = []
        for offset, delta, speed in ((0, 80, 16), (.1, 100, 24),
                                     (.2, 90, 8), (.3, 90, 0), (.5, 90, 0)):
            events.append(self.counter.update(start + offset, [target(x + delta, speed)]))
        return events

    def test_stillness_calibrates_without_counting(self):
        self.calibrate()
        for tick in range(12, 100):
            self.assertFalse(self.counter.update(tick / 10, [target()]))
        self.assertEqual(self.counter.count, 0)

    def test_one_burst_counts_only_after_quiet_and_only_once(self):
        self.calibrate()
        self.assertEqual(self.burst(), [False, False, False, False, True])
        for tick in range(18, 40):
            self.assertFalse(self.counter.update(tick / 10, [target(90)]))
        self.assertEqual(self.counter.count, 1)
        self.assertTrue(self.counter.ready)
        self.assertEqual(self.counter.last_event["peak_speed_cm_s"], 24)
        self.assertEqual(self.counter.last_event["displacement_mm"], 100)

    def test_two_bursts_after_quiet_and_cooldown(self):
        self.calibrate()
        self.burst()
        for tick in range(18, 25):
            self.counter.update(tick / 10, [target(90)])
        self.assertTrue(self.counter.ready)
        self.assertTrue(self.burst(start=2.5, x=90)[-1])
        self.assertEqual(self.counter.count, 2)

    def test_long_motion_does_not_repeat_count(self):
        self.calibrate()
        for tick in range(12, 50):
            self.assertFalse(self.counter.update(tick / 10, [target(100, 24)]))
        self.assertEqual(self.counter.count, 0)
        self.assertFalse(self.counter.ready)
        for tick in range(50, 63):
            self.counter.update(tick / 10, [target(100)])
        self.assertTrue(self.counter.ready)

    def test_isolated_spike_and_small_motion_do_not_count(self):
        self.calibrate()
        self.counter.update(1.2, [target(100, 24)])
        for tick in range(13, 18):
            self.counter.update(tick / 10, [target()])
        self.assertEqual(self.counter.count, 0)
        for t, x, speed in ((1.8, 10, 24), (1.9, 20, 24),
                            (2.0, 10, 0), (2.1, 10, 0), (2.3, 10, 0)):
            self.counter.update(t, [target(x, speed)])
        self.assertEqual(self.counter.count, 0)

    def test_equal_timestamp_does_not_supply_second_motion_sample(self):
        self.calibrate()
        self.counter.update(1.2, [target(80, 24)])
        for unused in range(20):
            self.assertFalse(self.counter.update(1.2, [target(100, 24)]))
        for tick in range(13, 18):
            self.counter.update(tick / 10, [target(90)])
        self.assertEqual(self.counter.count, 0)

    def test_stale_gap_backward_time_and_slot_change_cancel_candidate(self):
        for break_time, break_targets in (
            (1.8, [target(100, 24)]),
            (0.5, [target(100, 24)]),
            (1.4, [target(100, 24, slot=2)]),
        ):
            with self.subTest(break_time=break_time, targets=break_targets):
                self.counter.reset()
                self.calibrate()
                self.counter.update(1.2, [target(80, 24)])
                self.counter.update(1.3, [target(100, 24)])
                self.assertFalse(self.counter.update(break_time, break_targets))
                self.assertFalse(self.counter.ready)
                for index in range(1, 5):
                    self.counter.update(break_time + index / 10, [target(90, slot=break_targets[0].slot)])
                self.assertEqual(self.counter.count, 0)

    def test_missing_multiple_and_discontinuous_target_cancel_candidate(self):
        for break_targets in ([], [target(), target(10, slot=2)], [target(1500)]):
            with self.subTest(targets=break_targets):
                self.counter.reset()
                self.calibrate()
                self.counter.update(1.2, [target(80, 24)])
                self.counter.update(1.3, [target(100, 24)])
                self.assertFalse(self.counter.update(1.4, break_targets))
                self.assertFalse(self.counter.ready)
                self.assertEqual(self.counter.count, 0)

    def test_reacquisition_keeps_count_reset_clears_it(self):
        self.calibrate()
        self.burst()
        self.counter.update(1.8, [])
        self.assertEqual(self.counter.count, 1)
        self.calibrate(start=2.0, x=90)
        self.assertEqual(self.counter.count, 1)
        self.counter.reset()
        self.assertEqual(self.counter.count, 0)
        self.assertFalse(self.counter.ready)
        self.assertIsNone(self.counter.last_event)

    def test_begin_trial_preserves_ready_baseline_but_clears_old_count(self):
        self.calibrate()
        self.burst()
        for tick in range(18, 25):
            self.counter.update(tick / 10, [target(90)])
        self.assertTrue(self.counter.begin_trial())
        self.assertTrue(self.counter.ready)
        self.assertEqual(self.counter.count, 0)
        self.assertIsNone(self.counter.last_event)
        self.assertTrue(self.burst(start=2.5, x=90)[-1])
        self.assertEqual(self.counter.count, 1)

    def test_begin_trial_cannot_complete_preparation_movement(self):
        self.calibrate()
        self.counter.update(1.2, [target(80, 24)])
        self.counter.update(1.3, [target(100, 24)])
        self.assertFalse(self.counter.ready)
        self.assertFalse(self.counter.begin_trial())
        for tick in range(14, 20):
            self.assertFalse(self.counter.update(tick / 10, [target(90)]))
        self.assertEqual(self.counter.count, 0)
        self.assertFalse(self.counter.ready)

    def test_quiet_speed_with_unstable_position_cannot_calibrate(self):
        for tick in range(30):
            self.counter.update(tick / 10, [target(0 if tick % 2 else 100)])
        self.assertFalse(self.counter.ready)

    def test_walking_burst_can_count_expected_limitation(self):
        # A short sideways walking bout has the same input signature. This
        # deliberately documents why count is not a verified jump count.
        self.calibrate()
        self.burst()
        self.assertEqual(self.counter.count, 1)

    def test_settings_serializable_and_invalid_values_rejected(self):
        self.assertEqual(asdict(CounterSettings())["motion_speed_cm_s"], 16.0)
        for kwargs in ({"max_gap_seconds": 0}, {"motion_speed_cm_s": float("nan")},
                       {"quiet_speed_cm_s": 20}, {"motion_samples": 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                CounterSettings(**kwargs)


if __name__ == "__main__":
    unittest.main()
