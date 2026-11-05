"""Pencere kontrolunu ekran veya seri cihaz acmadan dogrula."""

import unittest
from unittest.mock import Mock, patch

try:
    from radar.window import RadarWindow
except ImportError:
    RadarWindow = None  # Tk is optional on headless CI systems.

from radar.counter import ExperimentalCounter
from radar.protocol import FrameParser
from radar.trial import TrialClock


@unittest.skipIf(RadarWindow is None, "Tk kurulu degil")
class WindowControllerTests(unittest.TestCase):
    def make_window(self):
        window = RadarWindow.__new__(RadarWindow)
        window.root = Mock()
        window.after_id = None
        window.connection = Mock(in_waiting=0)
        window.counter = ExperimentalCounter()
        window.parser = FrameParser()
        window.clock = TrialClock(duration=20)
        window.clock.start(100)
        window.started_at = 100
        window.last_frame = None
        window.reported_error = None
        window.game_port = None
        window.game_publisher = None
        window.game_status = Mock()
        window.recorder = Mock()
        window.recorder.summary = {"finish_reason": "in_progress", "active_frames": 0,
                                   "single_target_active_frames": 0}
        window.mode = Mock()
        window.mode.get.return_value = "Normal zıplama"
        for name in ("banner", "timer", "count_label", "instruction", "status", "telemetry",
                     "saved", "start_button", "stop_button", "save_button", "mode_box"):
            setattr(window, name, Mock())
        return window

    def test_deadline_closes_port_and_stops_polling_without_new_bytes(self):
        window = self.make_window()
        window.clock.advance(105, True)
        connection = window.connection
        with patch("radar.window.time.monotonic", return_value=125):
            window.poll()
        connection.close.assert_called_once()
        self.assertIsNone(window.connection)
        self.assertEqual(window.clock.phase, "done")
        window.root.after.assert_not_called()
        window.recorder.finish.assert_called_once()
        window.banner.config.assert_called_with(text="BİTTİ — DUR", fg="#a52020")

    def test_preparation_times_out_and_cannot_show_preparation_count(self):
        window = self.make_window()
        window.counter.count = 4
        connection = window.connection
        with patch("radar.window.time.monotonic", return_value=120):
            window.poll()
        connection.close.assert_called_once()
        self.assertEqual(window.counter.count, 0)
        self.assertEqual(window.clock.phase, "no_baseline")

    def test_cleanup_errors_do_not_leave_controls_running(self):
        window = self.make_window()
        window.clock.advance(105, True)
        window.connection.close.side_effect = OSError("unplugged")
        window.recorder.finish.side_effect = OSError("disk full")
        with patch("radar.window.time.monotonic", return_value=125):
            window.finish("done")
        self.assertIsNone(window.connection)
        window.recorder.finish.assert_called_once()
        window.start_button.config.assert_called_with(state="normal")
        window.stop_button.config.assert_called_with(state="disabled")
        window.save_button.config.assert_not_called()
        window.saved.config.assert_called_with(text="Kayıt hatası — dosyalar eksik olabilir.")

    def test_window_close_cancels_timer_and_releases_port(self):
        window = self.make_window()
        window.after_id = "timer1"
        connection = window.connection
        window.close()
        window.root.after_cancel.assert_called_with("timer1")
        connection.close.assert_called_once()
        window.root.destroy.assert_called_once()

    def game_window(self, phase):
        window = self.make_window()
        window.clock = Mock(phase=phase, active_at=105 if phase == "active" else None)
        window.clock.advance.return_value = phase
        window.clock.remaining.return_value = 10
        window.last_frame = 106
        window.connection.in_waiting = 30
        window.connection.read.return_value = bytes.fromhex(
            "AA FF 03 00 0E 03 B1 86 10 00 40 01" + " 00" * 16 + " 55 CC")
        window.counter = Mock(ready=True, count=1, status="Aday sayildi", last_event={"peak_speed_cm_s": 24})
        window.counter.update.return_value = True
        window.game_publisher = Mock()
        window.game_publisher.send_jump.return_value = {"source": "radar", "sequence": 1}
        window.recorder.summary["game_bridge"] = {"events_sent": 0}
        return window

    def test_only_active_detected_candidate_is_sent_once_and_recorded(self):
        window = self.game_window("active")
        with patch("radar.window.time.monotonic", return_value=106):
            window.poll()
        window.game_publisher.send_jump.assert_called_once_with()
        self.assertEqual(window.recorder.summary["game_bridge"]["events_sent"], 1)
        details = window.recorder.event.call_args.args[2]
        self.assertEqual(details["game_event"]["source"], "radar")
        self.assertEqual(details["peak_speed_cm_s"], 24)

    def test_preparation_or_non_candidate_does_not_send_game_input(self):
        for phase, detected in (("prepare", True), ("active", False)):
            with self.subTest(phase=phase, detected=detected):
                window = self.game_window(phase)
                window.counter.update.return_value = detected
                with patch("radar.window.time.monotonic", return_value=106):
                    window.poll()
                window.game_publisher.send_jump.assert_not_called()

    def test_game_send_failure_preserves_radar_recording_and_stops_publisher(self):
        window = self.game_window("active")
        publisher = window.game_publisher
        publisher.send_jump.side_effect = OSError("send failed")
        publisher.close.side_effect = OSError("close failed")
        with patch("radar.window.time.monotonic", return_value=106):
            window.poll()
        publisher.close.assert_called_once()
        self.assertIsNone(window.game_publisher)
        window.recorder.event.assert_called_once()
        window.recorder.frame.assert_called_once()
        window.recorder.finish.assert_not_called()
        window.root.after.assert_called_once()
        self.assertIn("error", window.recorder.summary["game_bridge"])
        self.assertIn("close_error", window.recorder.summary["game_bridge"])

    def test_finishing_trial_closes_game_publisher(self):
        window = self.game_window("active")
        publisher = window.game_publisher
        window.finish("done")
        publisher.close.assert_called_once()
        self.assertIsNone(window.game_publisher)

    def test_game_close_error_cannot_prevent_serial_and_file_cleanup(self):
        window = self.game_window("active")
        window.game_publisher.close.side_effect = OSError("close failed")
        connection = window.connection
        window.finish("done")
        connection.close.assert_called_once()
        window.recorder.finish.assert_called_once()
        self.assertIsNone(window.game_publisher)
        self.assertIsNone(window.connection)
        window.stop_button.config.assert_called_with(state="disabled")
