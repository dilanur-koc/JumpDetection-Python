import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from radar.protocol import FrameParser, decode_frame, signed_value
from radar.__main__ import main


# Hi-Link manual section 6 example: X=-782 mm, Y=1713 mm, speed=-16 cm/s.
EXAMPLE = bytes.fromhex("AA FF 03 00 0E 03 B1 86 10 00 40 01" + " 00" * 16 + " 55 CC")


class RadarTests(unittest.TestCase):
    def test_manufacturer_example(self):
        target, *empty = decode_frame(EXAMPLE)
        self.assertEqual((target.x_mm, target.y_mm, target.speed_cm_s, target.resolution_mm), (-782, 1713, -16, 320))
        self.assertTrue(target.present)
        self.assertTrue(all(not t.present for t in empty))

    def test_sign_magnitude_boundaries(self):
        self.assertEqual([signed_value(v) for v in (0, 0x8000, 0x7fff, 0xffff, 0x8010)], [0, 0, -32767, 32767, 16])

    def test_every_split_and_combined_frames(self):
        for split in range(1, 30):
            parser = FrameParser()
            self.assertEqual(parser.feed(EXAMPLE[:split]), [])
            self.assertEqual(parser.feed(EXAMPLE[split:] + EXAMPLE), [EXAMPLE, EXAMPLE])

    def test_noise_bad_footer_and_recovery(self):
        parser = FrameParser()
        bad = EXAMPLE[:-2] + b"xx"
        self.assertEqual(parser.feed(b"noise" + bad + EXAMPLE), [EXAMPLE])
        self.assertGreater(parser.discarded_bytes, 0)

    def test_noise_buffer_is_bounded(self):
        parser = FrameParser()
        parser.feed(b"x" * 100000)
        self.assertLessEqual(len(parser.buffer), 3)

    def test_invalid_frame_rejected(self):
        with self.assertRaises(ValueError):
            decode_frame(EXAMPLE[:-1])

    def test_replay_writes_empty_slots_and_label(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.jsonl"
            source.write_text(json.dumps({"elapsed_s": 1.0, "utc": "2026-10-29T20:00:00Z", "hex": EXAMPLE.hex()}) + "\n", encoding="utf-8")
            out = Path(folder) / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["--replay", str(source), "--output", str(out), "--label", "normal-jump"])
            self.assertEqual(result, 0)
            rows = next(out.glob("*.csv")).read_text().splitlines()
            self.assertEqual(len(rows), 4)
            self.assertIn("normal-jump,1,1,1,-782,1713,-16,320", rows[1])

    def test_no_frame_returns_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "empty.jsonl"
            source.write_text("", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--replay", str(source), "--output", str(Path(folder) / "out")]), 2)
