"""Hi-Link LD2450 raporlari: 30 bayt, little endian, isaret-buyukluk."""

from dataclasses import dataclass
import struct

HEADER = bytes.fromhex("AA FF 03 00")
FOOTER = bytes.fromhex("55 CC")


def signed_value(value):
    magnitude = value & 0x7FFF
    return magnitude if value & 0x8000 else -magnitude


@dataclass(frozen=True)
class Target:
    slot: int
    present: bool
    x_mm: int
    y_mm: int
    speed_cm_s: int
    resolution_mm: int


def decode_frame(frame):
    if len(frame) != 30 or not frame.startswith(HEADER) or not frame.endswith(FOOTER):
        raise ValueError("Gecersiz LD2450 raporu")
    targets = []
    for slot in range(3):
        payload = frame[4 + slot * 8:12 + slot * 8]
        x, y, speed, resolution = struct.unpack("<4H", payload)
        targets.append(Target(slot + 1, any(payload), signed_value(x),
                              signed_value(y), signed_value(speed), resolution))
    return targets


class FrameParser:
    def __init__(self):
        self.buffer = bytearray()
        self.discarded_bytes = 0

    def feed(self, chunk):
        self.buffer.extend(chunk)
        frames = []
        while True:
            start = self.buffer.find(HEADER)
            if start < 0:
                discard = max(0, len(self.buffer) - 3)
                self.discarded_bytes += discard
                del self.buffer[:discard]
                break
            self.discarded_bytes += start
            del self.buffer[:start]
            if len(self.buffer) < 30:
                break
            if self.buffer[28:30] != FOOTER:
                self.discarded_bytes += 1
                del self.buffer[0]
                continue
            frames.append(bytes(self.buffer[:30]))
            del self.buffer[:30]
        return frames
