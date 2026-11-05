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
        # İki yeni hızlı ölçüm, kısa durulma ve kısa bekleme: bütün döngü
        # bir saniyeden kısadır; denemede iki saniye ara vermek gerekmez.
        events = []
        for offset, delta, speed in ((0, 80, 16), (.08, 100, 24),
                                     (.16, 90, 8), (.28, 90, 0),
                                     (.42, 90, 0), (.56, 90, 0)):
            events.append(self.counter.update(start + offset, [target(x + delta, speed)]))
        return events

    def reach_timeout_recovery(self):
        self.calibrate()
        # Sürekli hareket, süre dolunca iptal olur; yeni hedef aramaya veya
        # yeni bir adayı tekrar tekrar saymaya dönüşmemelidir.
        for tick in range(12, 35):
            self.assertFalse(self.counter.update(tick / 10, [target(100, 24)]))
        self.assertEqual(self.counter.count, 0)
        self.assertFalse(self.counter.ready)

    def test_stillness_calibrates_without_counting(self):
        self.calibrate()
        for tick in range(12, 100):
            self.assertFalse(self.counter.update(tick / 10, [target()]))
        self.assertEqual(self.counter.count, 0)

    def test_one_burst_counts_only_after_quiet_and_only_once(self):
        self.calibrate()
        self.assertEqual(self.burst(), [False, False, False, True, False, False])
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
        self.assertTrue(self.burst(start=2.5, x=90)[3])
        self.assertEqual(self.counter.count, 2)

    def test_repeated_short_bouts_do_not_need_two_second_pauses(self):
        # Bunlar fiziksel zıplama kanıtı değil; kısa aralıklı girişlerin durum
        # makinesinde gereksiz beklemeye takılmadığını sınayan sentetik örnekler.
        for period in (.66, .72):
            with self.subTest(period=period):
                self.counter.reset()
                self.calibrate()
                for index in range(6):
                    events = self.burst(start=1.2 + index * period, x=index * 90)
                    self.assertEqual(sum(events), 1)
                    self.assertEqual(self.counter.count, index + 1)
                    self.assertTrue(self.counter.ready)

    def test_long_motion_does_not_repeat_count(self):
        self.calibrate()
        for tick in range(12, 50):
            self.assertFalse(self.counter.update(tick / 10, [target(100, 24)]))
        self.assertEqual(self.counter.count, 0)
        self.assertFalse(self.counter.ready)
        for tick in range(50, 63):
            self.counter.update(tick / 10, [target(100)])
        self.assertTrue(self.counter.ready)

    def test_timeout_recovers_with_brief_quiet_without_full_calibration(self):
        self.reach_timeout_recovery()
        self.assertFalse(self.counter.update(3.5, [target(100)]))
        self.assertFalse(self.counter.ready)
        self.assertFalse(self.counter.update(3.62, [target(100)]))
        self.assertTrue(self.counter.ready)
        self.assertEqual(self.counter.count, 0)
        self.assertTrue(self.burst(start=3.72, x=100)[3])
        self.assertEqual(self.counter.count, 1)

    def test_timeout_recovery_requires_fresh_quiet_not_elapsed_time(self):
        self.reach_timeout_recovery()
        for now in (3.6, 3.8):
            self.assertFalse(self.counter.update(now, [target(100, 24)]))
            self.assertFalse(self.counter.ready)
        self.assertFalse(self.counter.update(3.9, [target(100)]))
        for unused in range(10):
            self.assertFalse(self.counter.update(3.9, [target(100)]))
        self.assertFalse(self.counter.ready)
        self.assertFalse(self.counter.update(4.02, [target(100)]))
        self.assertTrue(self.counter.ready)
        self.assertEqual(self.counter.count, 0)

    def test_timeout_recovery_rejects_unstable_quiet_positions(self):
        self.reach_timeout_recovery()
        for now, x in ((3.5, 100), (3.62, 180), (3.74, 100), (3.86, 180)):
            self.assertFalse(self.counter.update(now, [target(x)]))
            self.assertFalse(self.counter.ready)
        self.assertFalse(self.counter.update(4.0, [target(180)]))
        self.assertTrue(self.counter.ready)
        self.assertEqual(self.counter.count, 0)

    def test_tracking_fault_during_recovery_requires_full_baseline(self):
        cases = (
            (3.5, [], 1),
            (3.5, [target(), target(10, slot=2)], 1),
            (3.5, [target(100, slot=2)], 2),
            (3.5, [target(1500)], 1),
            (3.9, [target(100, 24)], 1),  # Veri aralığı 0,4 saniyeyi aştı.
            (3.1, [target(100, 24)], 1),  # Zaman geriye gitti.
        )
        for break_time, break_targets, slot in cases:
            with self.subTest(break_time=break_time, targets=break_targets):
                self.counter.reset()
                self.reach_timeout_recovery()
                self.assertFalse(self.counter.update(break_time, break_targets))
                for offset in (.1, .22, .34, .46, .58):
                    self.assertFalse(self.counter.update(break_time + offset, [target(100, slot=slot)]))
                    self.assertFalse(self.counter.ready)
                self.assertEqual(self.counter.count, 0)
                # Kısa toparlanma yerine yeniden tam, kararlı referans gerekir.
                for tick in range(7, 15):
                    self.counter.update(break_time + tick / 10, [target(100, slot=slot)])
                self.assertTrue(self.counter.ready)
                self.assertEqual(self.counter.count, 0)

    def test_cooldown_needs_quiet_even_after_time_has_elapsed(self):
        self.calibrate()
        for now, x, speed in ((1.2, 80, 16), (1.28, 100, 24),
                               (1.36, 90, 0), (1.48, 90, 0)):
            self.counter.update(now, [target(x, speed)])
        self.assertEqual(self.counter.count, 1)
        for now in (1.6, 1.8, 2.0):
            self.assertFalse(self.counter.update(now, [target(100, 24)]))
            self.assertFalse(self.counter.ready)
        self.assertFalse(self.counter.update(2.1, [target(100)]))
        self.assertFalse(self.counter.ready)
        self.assertFalse(self.counter.update(2.22, [target(100)]))
        self.assertTrue(self.counter.ready)
        self.assertEqual(self.counter.count, 1)

    def test_configured_quiet_sample_count_is_required_in_addition_to_time(self):
        self.counter = ExperimentalCounter(CounterSettings(quiet_samples=3))
        self.calibrate()
        for now, x, speed in ((1.2, 80, 16), (1.28, 100, 24),
                               (1.36, 90, 0), (1.5, 90, 0)):
            self.assertFalse(self.counter.update(now, [target(x, speed)]))
        self.assertEqual(self.counter.count, 0)
        self.assertTrue(self.counter.update(1.6, [target(90)]))
        self.assertEqual(self.counter.count, 1)

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
        self.assertTrue(self.burst(start=2.5, x=90)[3])
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
        settings = asdict(CounterSettings())
        self.assertEqual(settings["motion_speed_cm_s"], 16.0)
        self.assertEqual(settings["motion_samples"], 2)
        self.assertEqual(settings["displacement_mm"], 60.0)
        self.assertEqual(settings["quiet_seconds"], .1)
        self.assertEqual(settings["quiet_samples"], 2)
        self.assertEqual(settings["cooldown_seconds"], .25)
        for kwargs in ({"max_gap_seconds": 0}, {"motion_speed_cm_s": float("nan")},
                       {"quiet_speed_cm_s": 20}, {"motion_samples": 1},
                       {"quiet_samples": 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                CounterSettings(**kwargs)


if __name__ == "__main__":
    unittest.main()
