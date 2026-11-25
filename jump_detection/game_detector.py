"""Camera game input for full-body and upper-body framing."""

from dataclasses import dataclass
from math import hypot, isfinite
from statistics import median

from .features import govde_y_hesapla


def landmarks_visible(points, indices):
    return len(points) > max(indices) and all(
        p.visibility >= 0.6 and isfinite(p.y) and isfinite(p.x)
        and 0 <= p.x <= 1 and 0 <= p.y <= 1
        for p in (points[i] for i in indices)
    )


@dataclass(frozen=True)
class BodySample:
    torso: float
    left_ankle: float
    right_ankle: float
    scale: float
    standing: bool

    @property
    def positions(self):
        return self.torso, self.left_ankle, self.right_ankle

    @classmethod
    def from_landmarks(cls, points):
        indices = (11, 12, 23, 24, 25, 26, 27, 28)
        if not landmarks_visible(points, indices):
            return None
        shoulder = (points[11].y + points[12].y) / 2
        hip = (points[23].y + points[24].y) / 2
        scale = hip - shoulder
        if scale <= 0.04:
            return None
        standing = all(points[knee].y - points[hip_index].y > 0.5 * scale
                       and points[ankle].y - points[knee].y > 0.5 * scale
                       for hip_index, knee, ankle in ((23, 25, 27), (24, 26, 28)))
        return cls(govde_y_hesapla(points), points[27].y, points[28].y, scale, standing)


@dataclass(frozen=True)
class UpperBodySample:
    # Laptop kamerasında ayaklar görünmeyebilir. Baş ve iki omuzdan bir örnek üretiriz.
    # scale fiziksel metre değil, görüntüdeki omuz açıklığından türetilen bir ölçektir.
    nose: float
    left_shoulder: float
    right_shoulder: float
    scale: float

    @property
    def positions(self):
        return self.nose, self.left_shoulder, self.right_shoulder

    @classmethod
    def from_landmarks(cls, points, aspect):
        if not landmarks_visible(points, (0, 11, 12)):
            return None
        nose, left, right = points[0], points[11], points[12]
        # Yatay omuz açıklığını dikey hareketle aynı görüntü-yüksekliği birimine çevir.
        scale = hypot((left.x - right.x) * aspect, left.y - right.y)
        if scale < 0.06 or nose.y >= min(left.y, right.y):
            return None
        return cls(nose.y, left.y, right.y, scale)


class CameraGameDetector:
    """Emit an upward motion event and rearm after returning to the reference."""

    def __init__(self, *, upper_body=False):
        self.upper_body = upper_body
        self.framing_hint = "SHOW HEAD AND BOTH SHOULDERS" if upper_body else "SHOW SHOULDERS, HIPS AND FEET"
        self.count = 0
        self._clear_tracking()

    def _clear_tracking(self):
        # Referans ve hareket geçmişini siler; toplam sayımı korur.
        # Böylece mesafe değişince yeniden kalibrasyon, eski sayımı kaybettirmez.
        self._samples = []
        self._baseline = None
        self._previous = None
        self._last_seen = None
        self._last_jump = None
        self._landed_since = None
        self.status = self.framing_hint

    def update(self, now, sample):
        # Bu metot kamera örneğinden yalnız bir olay kararı üretir; Unity'ye kendisi bağlanmaz.
        # now monotonik saniyedir. Eksik/eski görüntüyle hız tahmini yapılmaz.
        if self._last_seen is not None:
            gap = now - self._last_seen
            if gap <= 0:
                return False
            if gap > 0.25:
                self._clear_tracking()
        if sample is None:
            # Tek eksik kare hız ve iniş geçmişini keser; uzun kayıp referansı da siler.
            self._previous = None
            self._landed_since = None
            self._samples.clear()
            self.status = self.framing_hint
            return False
        previous = self._previous
        self._previous = (now, sample)
        self._last_seen = now
        if self._baseline is None:
            self._calibrate(now, sample)
            return False

        baseline_positions, baseline_scale = self._baseline
        if self.upper_body and abs(sample.scale / baseline_scale - 1) > 0.20:
            # Omuz genişliği %20'den fazla değişirse yeni mesafede sabit duruş referansı al.
            # Kalibrasyon sırasında olay üretilmez; önceki referansla yanlış kıyas yapılmaz.
            self._clear_tracking()
            self._previous = (now, sample)
            self._last_seen = now
            self._calibrate(now, sample)
            return False
        primary_rise, left_rise, right_rise = (
            (base - current) / baseline_scale
            for base, current in zip(baseline_positions, sample.positions)
        )

        # Aynı yükselişi her görüntü karesinde yeniden sayma. Referansa dönüş ve
        # kısa sabit duruş görülmeden bir sonraki olayı kabul etme.
        if self._last_jump is not None:
            if max(abs(left_rise), abs(right_rise), abs(primary_rise)) < 0.15:
                if self._landed_since is None:
                    self._landed_since = now
                if now - self._landed_since >= 0.12 and now - self._last_jump >= 0.45:
                    self._last_jump = None
                    self._landed_since = None
                    self.status = "READY - JUMP"
            else:
                self._landed_since = None
            return False

        if previous is None:
            return False
        previous_time, previous_sample = previous
        speed = (previous_sample.positions[0] - sample.positions[0]) / (baseline_scale * (now - previous_time))
        rises = primary_rise, left_rise, right_rise
        # Görüntüde Y aşağı büyür; önceki Y - yeni Y pozitifse yukarı hareket vardır.
        # Baş sallamak/tek omzu kaldırmak yerine üç noktanın tutarlı yükselişini ara.
        coherent = not self.upper_body or max(rises) - min(rises) <= 0.14
        if coherent and primary_rise >= 0.16 and min(left_rise, right_rise) >= 0.12 and speed >= 0.45:
            self.count += 1
            self._last_jump = now
            self.status = ("MOTION SENT - RETURN TO START" if self.upper_body
                           else "JUMP SENT - WAIT FOR LANDING")
            return True
        self.status = "READY - JUMP"
        return False

    def _calibrate(self, now, sample):
        # En az 8 örnek ve 1 saniyelik kararlı duruş gerekir. Medyan, tek karedeki
        # küçük sapmaların referansı bozmasını azaltır. Bu bir hareket referansıdır.
        self.status = ("CALIBRATING - STAND STILL" if self.upper_body
                       else "CALIBRATING - STAND STILL, FEET IN VIEW")
        if isinstance(sample, BodySample) and not sample.standing:
            self._samples.clear()
            return
        if self._samples:
            first = self._samples[0][1]
            drift = max(abs(a - b) for a, b in zip(sample.positions, first.positions))
            if self.upper_body:
                drift = max(drift, abs(sample.scale - first.scale))
            if drift > 0.12 * first.scale:
                self._samples.clear()
        self._samples.append((now, sample))
        if len(self._samples) < 8 or now - self._samples[0][0] < 1.0:
            return
        samples = [entry[1] for entry in self._samples]
        self._baseline = (tuple(median(axis) for axis in zip(*(s.positions for s in samples))),
                          median(s.scale for s in samples))
        self._samples.clear()
        self.status = "READY - JUMP"
