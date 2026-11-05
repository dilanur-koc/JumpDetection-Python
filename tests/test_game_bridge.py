"""Seri port, kamera veya Unity istemeyen gercek loopback kopru testleri."""

import contextlib
from decimal import Decimal
import io
import json
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from uuid import UUID

from game_bridge import (EVENT_FIELDS, GameEventPublisher, GameEventValidator,
                         HOST, MAX_INT64, MAX_PACKET_BYTES, SOURCE_EVIDENCE)
from game_bridge.__main__ import listen, main, simulate


NOW = 1700000000.0


def event(**changes):
    result = {
        "schema_version": 1, "event_type": "jump_request", "source": "simulator",
        "evidence": "simulated", "experimental": False,
        "session_id": "00000000000040008000000000000001", "sequence": 1,
        "sent_at_unix_ms": int(NOW * 1000),
    }
    result.update(changes)
    return result


def packet(**changes):
    return json.dumps(event(**changes)).encode("utf-8")


class GameBridgeTests(unittest.TestCase):
    def validator(self, **kwargs):
        return GameEventValidator(clock=lambda: NOW, **kwargs)

    def test_real_loopback_publish_validate_and_sequence(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind((HOST, 0))
            receiver.settimeout(1)
            with GameEventPublisher("simulator", receiver.getsockname()[1], clock=lambda: NOW) as publisher:
                for sequence in (1, 2):
                    sent = publisher.send_jump()
                    data, address = receiver.recvfrom(2048)
                    self.assertEqual(address[0], HOST)
                    self.assertEqual(sent, self.validator().accept(data))
                    self.assertEqual(set(sent), EVENT_FIELDS)
                    self.assertEqual(sent["sequence"], sequence)
                    self.assertEqual(UUID(hex=sent["session_id"]).version, 4)

    def test_each_source_has_fixed_evidence_and_experimental_flag(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind((HOST, 0))
            receiver.settimeout(1)
            for source, (evidence, experimental) in SOURCE_EVIDENCE.items():
                with self.subTest(source=source), GameEventPublisher(source, receiver.getsockname()[1], clock=lambda: NOW) as publisher:
                    result = publisher.send_jump()
                    data, address = receiver.recvfrom(2048)
                    self.assertEqual(result["evidence"], evidence)
                    self.assertIs(result["experimental"], experimental)
                    self.assertEqual(self.validator(source=source).accept(data), result)

    def test_close_is_idempotent_and_closed_send_raises(self):
        publisher = GameEventPublisher("simulator")
        publisher.close()
        publisher.close()
        with self.assertRaises(OSError):
            publisher.send_jump()

    def test_socket_error_is_not_hidden_or_counted_as_success(self):
        with GameEventPublisher("simulator") as publisher:
            publisher._socket.close()
            with self.assertRaises(OSError):
                publisher.send_jump()
            self.assertEqual(publisher.sequence, 0)

    def test_bad_fields_types_and_nonfinite_values_are_rejected(self):
        invalid = (
            packet(schema_version=True), packet(schema_version=2), packet(sequence=True),
            packet(sequence=0), packet(sequence=1.5), packet(sent_at_unix_ms=float("nan")),
            packet(sent_at_unix_ms=float("inf")), packet(sent_at_unix_ms=NOW * 1000),
            packet(session_id="not-a-session"), packet(session_id="A" * 32),
            packet(experimental=0), packet(experimental=True), packet(evidence="motion_candidate"),
            packet(event_type="jump"), packet(extra="unknown"), b"[]", b"null", b"{broken",
            b"\xff", b"x" * (MAX_PACKET_BYTES + 1),
        )
        for data in invalid:
            with self.subTest(packet=data[:80]):
                validator = self.validator()
                self.assertIsNone(validator.accept(data))
                self.assertIsNotNone(validator.accept(packet()))
        missing = event()
        missing.pop("evidence")
        self.assertIsNone(self.validator().accept(json.dumps(missing)))
        duplicated = packet().decode().replace('"sequence": 1', '"sequence": 1, "sequence": 2')
        self.assertIsNone(self.validator().accept(duplicated))

    def test_source_filter_does_not_consume_session_sequence(self):
        validator = self.validator()
        self.assertIsNone(validator.accept(packet(source="radar", evidence="motion_candidate", experimental=True)))
        self.assertIsNone(validator.accept(packet(source="unknown")))
        self.assertIsNotNone(validator.accept(packet()))

    def test_age_and_future_boundaries(self):
        for age_ms, accepted in ((999, True), (1000, False), (-250, True), (-251, False)):
            with self.subTest(age_ms=age_ms):
                result = self.validator().accept(packet(sent_at_unix_ms=int(NOW * 1000) - age_ms))
                self.assertEqual(result is not None, accepted)

    def test_int64_bounds_match_unity_fields_without_float_rounding(self):
        self.assertIsNotNone(self.validator().accept(packet(sequence=MAX_INT64)))
        self.assertIsNone(self.validator().accept(packet(sequence=MAX_INT64 + 1)))
        clock = lambda: Decimal(MAX_INT64) / 1000
        validator = GameEventValidator(clock=clock)
        self.assertIsNotNone(validator.accept(packet(sent_at_unix_ms=MAX_INT64)))
        self.assertIsNone(GameEventValidator(clock=clock).accept(packet(sent_at_unix_ms=MAX_INT64 + 1)))
        self.assertIsNone(self.validator().accept(packet(sent_at_unix_ms=-1)))

    def test_publisher_rejects_unrepresentable_sequence_or_timestamp(self):
        with GameEventPublisher("simulator", clock=lambda: NOW) as publisher:
            publisher.sequence = MAX_INT64
            with self.assertRaises(OSError):
                publisher.send_jump()
            self.assertEqual(publisher.sequence, MAX_INT64)
        with GameEventPublisher("simulator", clock=lambda: Decimal(MAX_INT64 + 1) / 1000) as publisher:
            with self.assertRaises(OSError):
                publisher.send_jump()
            self.assertEqual(publisher.sequence, 0)

    def test_deep_json_cannot_crash_receiver(self):
        # Boyut sınırının içinde olsa bile aşırı iç içe JSON hata verebilir.
        nested = b"[" * 1000 + b"0" + b"]" * 1000
        self.assertLess(len(nested), MAX_PACKET_BYTES)
        self.assertIsNone(self.validator().accept(nested))

    def test_duplicate_reorder_and_distinct_session(self):
        validator = self.validator()
        self.assertIsNotNone(validator.accept(packet(sequence=2)))
        self.assertIsNone(validator.accept(packet(sequence=2)))
        self.assertIsNone(validator.accept(packet(sequence=1)))
        self.assertIsNotNone(validator.accept(packet(sequence=3)))
        self.assertIsNotNone(validator.accept(packet(session_id="1" * 32)))

    def test_invalid_high_sequence_cannot_poison_valid_session(self):
        validator = self.validator()
        self.assertIsNone(validator.accept(packet(sequence=1000, sent_at_unix_ms=int(NOW * 1000) - 1000)))
        self.assertIsNotNone(validator.accept(packet()))

    def test_session_memory_has_sixty_four_entry_limit(self):
        validator = self.validator()
        for index in range(65):
            self.assertIsNotNone(validator.accept(packet(session_id=f"{index:032x}")))
        self.assertEqual(len(validator._sequences), 64)
        self.assertNotIn(f"{0:032x}", validator._sequences)
        self.assertIn(f"{64:032x}", validator._sequences)

    def test_simulator_sends_finite_actual_loopback_packets_without_sleep_after_last(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind((HOST, 0))
            receiver.settimeout(1)
            output, waits = [], []
            self.assertEqual(simulate(5, .7, receiver.getsockname()[1], emit=output.append, sleep=waits.append), 5)
            received = [json.loads(receiver.recvfrom(2048)[0]) for unused in range(5)]
        self.assertEqual([item["sequence"] for item in received], [1, 2, 3, 4, 5])
        self.assertEqual(len({item["session_id"] for item in received}), 1)
        self.assertEqual([json.loads(line) for line in output], received)
        self.assertEqual(waits, [.7] * 4)

    def test_listener_stops_when_idle(self):
        start = time.monotonic()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(listen(.08, port=0, emit=lambda line: self.fail("Beklenmeyen olay")), 0)
        self.assertLess(time.monotonic() - start, 1.0)

    def test_cli_validates_nonfinite_intervals_and_counts(self):
        for arguments in (["simulate", "--count", "0"], ["simulate", "--interval", "nan"],
                          ["simulate", "--interval", "inf"], ["listen", "--seconds", "inf"],
                          ["listen", "--seconds", "0"]):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(arguments)
                self.assertEqual(raised.exception.code, 2)

    def test_cli_sender_needs_no_third_party_hardware_imports(self):
        # Testler varsayılan oyun portuna komut yollamaz; kendilerine ait
        # geçici portu kullanır, açık bir Unity sahnesini etkilemezler.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind((HOST, 0))
            port = receiver.getsockname()[1]
            code = (
                "import sys; from game_bridge.__main__ import main; "
                f"result=main(['simulate','--count','2','--interval','0','--port','{port}']); "
                "assert not any(m in sys.modules for m in ['serial','cv2','mediapipe','tkinter']); "
                "raise SystemExit(result)"
            )
            result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parent.parent,
                                    capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
