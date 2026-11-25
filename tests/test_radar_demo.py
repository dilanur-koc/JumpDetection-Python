"""Demo sensitivity and rearming; not proof of physical jump accuracy."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from radar.counter import CounterSettings, ExperimentalCounter
from radar.protocol import Target
from radar.trial import TrialRecorder
from radar.__main__ import main


def target(x=0, speed=0, slot=1):
    return Target(slot, True, x, 1000, speed, 320)


class DemoTests(unittest.TestCase):
    def calibrated(self, demo=True):
        c = ExperimentalCounter(CounterSettings.for_demo(2500) if demo else CounterSettings())
        for i in range(12):
            c.update(i / 10, [target()])
        self.assertTrue(c.ready)
        return c

    def test_demo_confirms_movement_without_waiting_for_it_to_end(self):
        normal = self.calibrated(False)
        demo = self.calibrated()
        self.assertFalse(normal.update(1.2, [target(40, 16)]))
        self.assertFalse(demo.update(1.2, [target(40, 16)]))
        self.assertTrue(demo.update(1.3, [target(50, 16)]))
        self.assertTrue(demo.last_event["demo_mode"])
        self.assertEqual(demo.last_event["trigger"], "radar_motion_onset")
        self.assertEqual(demo.count, 1)

    def test_demo_requires_speed_and_displacement_and_does_not_count_stillness(self):
        for x, speed in ((0, 0), (100, 0), (0, 16), (10, 16), (40, 8)):
            with self.subTest(x=x, speed=speed):
                c = self.calibrated()
                self.assertFalse(c.update(1.2, [target(x, speed)]))
                self.assertFalse(c.update(1.3, [target(x, speed)]))
                self.assertEqual(c.count, 0)

    def test_isolated_speed_spikes_cannot_trigger_demo(self):
        c = self.calibrated()
        self.assertFalse(c.update(1.2, [target(90, 39)]))
        self.assertFalse(c.update(1.2, [target(90, 39)]))
        self.assertFalse(c.update(1.3, [target(90, 8)]))
        self.assertFalse(c.update(1.4, [target(95, 24)]))
        self.assertEqual(c.count, 0)
        self.assertTrue(c.update(1.5, [target(95, 24)]))

    def test_demo_requires_quiet_and_cooldown_before_rearming(self):
        c = self.calibrated()
        self.assertFalse(c.update(1.2, [target(40, 16)]))
        self.assertTrue(c.update(1.3, [target(50, 16)]))
        for i in range(14, 26):
            self.assertFalse(c.update(i / 10, [target(60, 16)]))
        self.assertEqual(c.count, 1)
        c.update(2.6, [target(60, 0)])
        c.update(2.72, [target(60, 0)])
        self.assertTrue(c.ready)
        self.assertFalse(c.update(2.8, [target(100, 16)]))
        self.assertTrue(c.update(2.9, [target(105, 16)]))
        self.assertEqual(c.count, 2)

    def test_demo_still_rejects_missing_multiple_stale_and_teleporting_targets(self):
        cases = [(1.2, []), (1.2, [target(40, 16), target(60, 16, 2)]),
                 (2.0, [target(40, 16)]), (1.2, [target(800, 16)]),
                 (1.2, [target(3000, 16)])]
        for time, targets in cases:
            with self.subTest(time=time, targets=targets):
                c = self.calibrated()
                self.assertFalse(c.update(time, targets))
                self.assertEqual(c.count, 0)
                self.assertFalse(c.ready)

    def test_range_rejects_near_target_but_still_requires_one_player(self):
        c = ExperimentalCounter(CounterSettings.for_demo(2500, min_distance_mm=800))
        near = Target(2, True, 0, 250, 32, 320)
        for i in range(12):
            self.assertFalse(c.update(i / 10, [target(), near]))
        self.assertTrue(c.ready)
        self.assertFalse(c.update(1.2, [target(40, 16), near]))
        self.assertTrue(c.update(1.3, [target(50, 16), near]))
        self.assertFalse(c.update(1.4, [target(50, 16), target(300, 16, slot=2)]))
        self.assertEqual(c.status, "Birden fazla hedef")

    def test_demo_is_explicit_in_cli_and_recording(self):
        with patch("radar.window.main", return_value=0) as launch:
            self.assertEqual(main(["--counter-window", "--game-events", "--demo-game"]), 0)
            self.assertTrue(launch.call_args.kwargs["demo_game"])
            main(["--counter-window", "--game-events"])
            self.assertNotIn("demo_game", launch.call_args.kwargs)
        with tempfile.TemporaryDirectory() as folder:
            recorder = TrialRecorder(Path(folder), "normal-jump", CounterSettings.for_demo(2500), "COM5", 256000, None)
            recorder.finish("stopped", 0, 0, 0)
            summary = json.loads(recorder.summary_path.read_text())
            self.assertTrue(summary["settings"]["demo_mode"])
            self.assertIn("DEMO", summary["count_semantics"])

    def test_sitting_like_motion_also_triggers_documented_demo_limitation(self):
        c = self.calibrated()
        self.assertFalse(c.update(1.2, [target(100, 24)]))
        self.assertTrue(c.update(1.3, [target(105, 24)]))
        self.assertEqual(c.count, 1)
