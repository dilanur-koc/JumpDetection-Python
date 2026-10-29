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
