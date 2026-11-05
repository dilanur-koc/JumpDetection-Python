"""Yerel oyun girdisi koprusu; olay fiziksel ziplama dogrulamasi degildir."""

from collections import OrderedDict
import json
import re
import socket
import time
from uuid import uuid4


HOST = "127.0.0.1"
DEFAULT_PORT = 5065
MAX_PACKET_BYTES = 2048
MAX_INT64 = (1 << 63) - 1
SOURCE_EVIDENCE = {
    "simulator": ("simulated", False),
    "radar": ("motion_candidate", True),
    "camera": ("camera_estimate", True),
}
EVENT_FIELDS = frozenset((
    "schema_version", "event_type", "source", "evidence", "experimental",
    "session_id", "sequence", "sent_at_unix_ms",
))


def _port(value, allow_zero=False):
    if type(value) is not int or not (0 if allow_zero else 1) <= value <= 65535:
        raise ValueError("Port 1 ile 65535 arasinda bir tam sayi olmali")
    return value


class GameEventPublisher:
    """Tek Python oturumunun ziplama isteklerini yalniz localhost'a yollar."""

    def __init__(self, source, port=DEFAULT_PORT, *, clock=None):
        if not isinstance(source, str) or source not in SOURCE_EVIDENCE:
            raise ValueError("Bilinmeyen girdi kaynagi")
        self.port = _port(port)
        self.source = source
        self.session_id = uuid4().hex
        self.sequence = 0
        self.clock = clock or time.time
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._closed = False

    def send_jump(self):
        if self._closed:
            raise OSError("Olay yayincisi kapali")
        if self.sequence >= MAX_INT64:
            raise OSError("Olay sira numarasi Int64 sinirini asti")
        try:
            sent_ms = int(self.clock() * 1000)
        except (TypeError, ValueError, OverflowError) as exc:
            raise OSError("Olay icin gecersiz saat degeri") from exc
        if not 0 <= sent_ms <= MAX_INT64:
            raise OSError("Unix zamani Int64 araliginda olmali")
        evidence, experimental = SOURCE_EVIDENCE[self.source]
        event = {
            "schema_version": 1,
            "event_type": "jump_request",
            "source": self.source,
            "evidence": evidence,
            "experimental": experimental,
            "session_id": self.session_id,
            "sequence": self.sequence + 1,
            # Unix zamanı UTC milisaniyedir; alıcı olayın bayatlığını bununla denetler.
            "sent_at_unix_ms": sent_ms,
        }
        payload = json.dumps(event, allow_nan=False, separators=(",", ":")).encode("utf-8")
        # UDP gönderimi teslim onayı değildir; alıcı yoksa gönderim yine başarılı olabilir.
        self._socket.sendto(payload, (HOST, self.port))
        self.sequence = event["sequence"]
        return event

    def close(self):
        if not self._closed:
            self._closed = True
            self._socket.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Tekrarlanan JSON alani")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("NaN ve sonsuz sayilar JSON olayinda kullanilamaz")


class GameEventValidator:
    """Secili kaynagin yeni ve sirali olaylarini kabul eden tani dogrulayicisi."""

    def __init__(self, source="simulator", *, clock=None, max_sessions=64):
        if not isinstance(source, str) or source not in SOURCE_EVIDENCE:
            raise ValueError("Bilinmeyen girdi kaynagi")
        if type(max_sessions) is not int or not 1 <= max_sessions <= 64:
            raise ValueError("Oturum siniri 1 ile 64 arasinda olmali")
        self.source = source
        self.clock = clock or time.time
        self.max_sessions = max_sessions
        self._sequences = OrderedDict()

    def accept(self, packet):
        """Gecersiz/tekrar/bayat olay icin None, kabul edilirse olay sozlugu dondur."""
        try:
            if not isinstance(packet, (bytes, str)):
                return None
            if isinstance(packet, str):
                packet = packet.encode("utf-8")
            if len(packet) > MAX_PACKET_BYTES:
                return None
            event = json.loads(packet.decode("utf-8"), object_pairs_hook=_strict_object,
                               parse_constant=_invalid_constant)
            if not isinstance(event, dict) or set(event) != EVENT_FIELDS:
                return None
            if type(event["schema_version"]) is not int or event["schema_version"] != 1:
                return None
            if event["event_type"] != "jump_request" or event["source"] != self.source:
                return None
            evidence, experimental = SOURCE_EVIDENCE[self.source]
            if event["evidence"] != evidence:
                return None
            if type(event["experimental"]) is not bool or event["experimental"] != experimental:
                return None
            session, sequence, sent = event["session_id"], event["sequence"], event["sent_at_unix_ms"]
            if not isinstance(session, str) or re.fullmatch(r"[0-9a-f]{32}", session) is None:
                return None
            # Unity/C# long alanlarıyla aynı Int64 aralığını kullanırız.
            if (type(sequence) is not int or not 1 <= sequence <= MAX_INT64
                    or type(sent) is not int or not 0 <= sent <= MAX_INT64):
                return None
            age_ms = int(self.clock() * 1000) - sent
            if age_ms >= 1000 or age_ms < -250:
                return None
            if sequence <= self._sequences.get(session, 0):
                return None
            # Bellek sınırlıdır: en son kullanılan 64 oturumun sıra numarası tutulur.
            self._sequences[session] = sequence
            self._sequences.move_to_end(session)
            while len(self._sequences) > self.max_sessions:
                self._sequences.popitem(last=False)
            return event
        except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
            return None
