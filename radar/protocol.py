"""Hi-Link LD2450 raporlari: 30 bayt, little endian, isaret-buyukluk."""

from dataclasses import dataclass
import struct

# Bir rapor: 4 bayt başlık + üç adet 8 bayt hedef alanı + 2 bayt son işareti.
# Bu sabitler seri bayt akışı içinde rapor sınırlarını bulmamızı sağlar.
HEADER = bytes.fromhex("AA FF 03 00")
FOOTER = bytes.fromhex("55 CC")


def signed_value(value):
    # LD2450 işaret-büyüklük kodlar: en yüksek bit 1 ise pozitif, 0 ise negatif.
    # Bu, Python'un alışılmış ikiye tümleyen işaretli tamsayı çözümü değildir.
    # Kalan 15 bit büyüklüktür; bu nedenle alanları önce işaretsiz okuruz.
    magnitude = value & 0x7FFF
    return magnitude if value & 0x8000 else -magnitude


@dataclass(frozen=True)
class Target:
    # Bir rapordaki ölçümleri değiştirilemez bir nesnede bir arada tutarız.
    # slot 1–3 bir rapor yuvasıdır; kalıcı kişi kimliği olarak yorumlanmaz.
    # X/Y radar düzleminde mm, hız cm/sn; Y dikey zıplama yüksekliği değildir.
    slot: int
    present: bool
    x_mm: int
    y_mm: int
    speed_cm_s: int
    resolution_mm: int


def decode_frame(frame):
    # Yalnız boyutu ve sınır işaretleri doğru olan tam raporları çözümleriz.
    # Rapor checksum içermediği için her veri bozulmasını yakalamak mümkün değildir.
    if len(frame) != 30 or not frame.startswith(HEADER) or not frame.endswith(FOOTER):
        raise ValueError("Gecersiz LD2450 raporu")
    targets = []
    for slot in range(3):
        # Her yuvada sırasıyla X, Y, hız ve mesafe çözünürlüğü bulunur.
        payload = frame[4 + slot * 8:12 + slot * 8]
        # < little endian demektir: düşük anlamlı bayt önce gelir; H 16 bittir.
        x, y, speed, resolution = struct.unpack("<4H", payload)
        # Sekiz baytın tamamı sıfırsa bu yuvada raporlanan hedef yoktur.
        targets.append(Target(slot + 1, any(payload), signed_value(x),
                              signed_value(y), signed_value(speed), resolution))
    return targets


class FrameParser:
    # Seri okumalar paketi bölebilir veya birkaç paketi birleştirebilir.
    # Tampon, çağrılar arasında eksik baytları koruyarak akışı yeniden birleştirir.
    def __init__(self):
        self.buffer = bytearray()
        self.discarded_bytes = 0

    def feed(self, chunk):
        # Her çağrı sıfır, bir veya birden fazla tamamlanmış rapor döndürebilir.
        self.buffer.extend(chunk)
        frames = []
        while True:
            start = self.buffer.find(HEADER)
            if start < 0:
                # Dört baytlık başlığın ilk üç baytı sonda kalmış olabilir.
                # Onları korur, başlık olamayacak eski gürültüyü atarız.
                discard = max(0, len(self.buffer) - 3)
                self.discarded_bytes += discard
                del self.buffer[:discard]
                break
            # Başlıktan önceki gürültüyü atarak yeniden paket hizasına geliriz.
            self.discarded_bytes += start
            del self.buffer[:start]
            if len(self.buffer) < 30:
                # Paket henüz tamamlanmadı; sonraki okuma parçasını bekleriz.
                break
            if self.buffer[28:30] != FOOTER:
                # Son işareti yanlışsa tek bayt ilerleyip yeni başlık ararız.
                # Tam bir paket boyu atlamak, aradaki sağlam başlığı kaçırabilir.
                self.discarded_bytes += 1
                del self.buffer[0]
                continue
            # Tam raporu ayırır, tamponda kalan diğer raporları aramaya devam ederiz.
            frames.append(bytes(self.buffer[:30]))
            del self.buffer[:30]
        return frames
