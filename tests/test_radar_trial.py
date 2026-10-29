import csv
import json
from pathlib import Path
import tempfile
import unittest

from radar.counter import CounterSettings
from radar.protocol import Target
from radar.trial import TrialClock, TrialRecorder


class TrialTests(unittest.TestCase):
    def test_preparation_waits_for_baseline_then_full_trial_duration(self):
        clock = TrialClock(duration=20)
        clock.start(100)
        self.assertEqual(clock.advance(104, True), "prepare")
        self.assertEqual(clock.advance(105, False), "prepare")
        self.assertEqual(clock.advance(107, True), "active")
        self.assertEqual(clock.remaining(108), 19)
        self.assertEqual(clock.advance(126.99, True), "active")
        self.assertEqual(clock.advance(127, False), "done")
        self.assertEqual(clock.advance(200, True), "done")

    def test_no_data_preparation_times_out(self):
        clock = TrialClock()
        clock.start(10)
        self.assertEqual(clock.advance(29, False), "prepare")
        self.assertEqual(clock.advance(30, False), "no_baseline")
        self.assertIsNone(clock.active_at)

    def test_restart_clears_previous_trial_timing(self):
        clock = TrialClock()
        clock.start(0)
        clock.advance(5, True)
        clock.advance(25, True)
        clock.start(100)
        self.assertEqual(clock.phase, "prepare")
        self.assertIsNone(clock.active_at)
        self.assertEqual(clock.remaining(101), 4)

    def test_delayed_ready_callback_cannot_start_after_hard_deadline(self):
        clock = TrialClock()
        clock.start(100)
        self.assertEqual(clock.advance(121, True), "no_baseline")
        self.assertIsNone(clock.active_at)

    def test_raw_csv_events_settings_and_actual_count_saved_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = TrialRecorder(directory, "walking", CounterSettings(), "COM5", 256000, 20)
            record = recorder.chunk(5.2, b"test", "active")
            targets = [Target(1, True, 10, 1000, 24, 320), Target(2, False, 0, 0, 0, 0)]
            recorder.frame(record, targets, 1, "Aday sayildi")
            recorder.event(record, 1, {"peak_speed_cm_s": 24})
            recorder.finish("done", 1, 3, 1)
            summary = json.loads(recorder.summary_path.read_text(encoding="utf-8"))
            self.assertIsNone(summary["reported_jump_count"])
            self.assertEqual(summary["candidate_count"], 1)
            self.assertEqual(summary["single_target_active_frames"], 1)
            self.assertEqual(summary["settings"]["motion_speed_cm_s"], 16)
            recorder.report_actual(0)
            self.assertEqual(json.loads(recorder.summary_path.read_text(encoding="utf-8"))["reported_jump_count"], 0)
            with recorder.base.with_suffix(".csv").open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["candidate_count"], "1")
            self.assertEqual(json.loads(recorder.base.with_suffix(".jsonl").read_text())["phase"], "active")
            self.assertEqual(json.loads(recorder.base.with_suffix(".events.jsonl").read_text())["count"], 1)
            with self.assertRaises(ValueError):
                recorder.report_actual(-1)
