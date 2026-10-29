"""Deneysel hareket adayi sayaci; dikey ziplama siniflandiricisi degildir.

LD2450'nin radar duzlemindeki konumu ve sensor hizi kullanilir. Yurumek,
comelmek veya baska bir hareket de kosullari saglayabilir. Esikler ilk
deneme icindir; fiziksel dogrulama olmadan ziplama basarimi ifade etmez.
"""

from dataclasses import dataclass
from math import hypot, isfinite
from statistics import median


@dataclass(frozen=True)
class CounterSettings:
    motion_speed_cm_s: float = 16.0
    quiet_speed_cm_s: float = 8.0
    motion_samples: int = 2
    quiet_seconds: float = 0.25
    displacement_mm: float = 60.0
    baseline_seconds: float = 1.0
    baseline_samples: int = 5
    baseline_radius_mm: float = 50.0
    max_burst_seconds: float = 2.0
    cooldown_seconds: float = 0.6
    max_gap_seconds: float = 0.4
    max_step_mm: float = 500.0

    def __post_init__(self):
        for name in (
            "motion_speed_cm_s", "quiet_seconds", "displacement_mm",
            "baseline_seconds", "baseline_radius_mm", "max_burst_seconds",
            "max_gap_seconds", "max_step_mm",
        ):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} pozitif ve sonlu olmali")
        if (not isfinite(self.quiet_speed_cm_s) or self.quiet_speed_cm_s < 0
                or self.quiet_speed_cm_s >= self.motion_speed_cm_s):
            raise ValueError("Sessizlik esigi hareket esiginden kucuk olmali")
        if not isfinite(self.cooldown_seconds) or self.cooldown_seconds < 0:
            raise ValueError("Bekleme suresi negatif olmamali")
        if self.max_burst_seconds <= self.quiet_seconds:
            raise ValueError("Hareket penceresi sessizlik suresinden uzun olmali")
        for name in ("motion_samples", "baseline_samples"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 2:
                raise ValueError(f"{name} en az iki taze ornek olmali")


class ExperimentalCounter:
    """Tek hedefin hizli hareket + yer degistirme + durulma dongusunu sayar.

    Olay ancak hareket bittikten sonra sayilir. Eslik eden hedef degisimi,
    veri kaybi ve buyuk konum sicramasi bekleyen adayi iptal eder. Tek basina
    yuva numarasi kisi kimligi degildir; bu arac tek kisilik deney icindir.
    """

    def __init__(self, settings=None):
        self.settings = settings or CounterSettings()
        self.reset()

    def reset(self):
        self.count = 0
        self.last_event = None
        self._last_time = None
        self._last_count_time = float("-inf")
        self._invalidate("Kalibrasyon: sabit durun")

    def begin_trial(self):
        """Hazirlik sayimini/pending hareketini temizle; hazirsa referansi koru.

        True aktif denemenin hazir referansla baslayabilecegini belirtir.
        Hareket sirasinda cagirilirsa eski aday iptal edilir ve False doner;
        yeni bir kararli kalibrasyon gereklidir.
        """
        self.count = 0
        self.last_event = None
        self._last_count_time = float("-inf")
        if not self.ready or self._mode != "ready":
            self._invalidate("Kalibrasyon: sabit durun")
            return False
        self._quiet_points = []
        self._burst_started = None
        self._motion_streak = 0
        self._enough_motion = False
        self._peak_speed = 0.0
        self._peak_displacement = 0.0
        self.status = "Hazir"
        return True

    def _invalidate(self, status):
        self.ready = False
        self.status = status
        self._mode = "baseline"
        self._slot = None
        self._last_point = None
        self._baseline_points = []
        self._baseline = None
        self._quiet_points = []
        self._burst_started = None
        self._motion_streak = 0
        self._enough_motion = False
        self._peak_speed = 0.0
        self._peak_displacement = 0.0

    @staticmethod
    def _center(points):
        return (median(p[1][0] for p in points),
                median(p[1][1] for p in points))

    @staticmethod
    def _distance(a, b):
        return hypot(a[0] - b[0], a[1] - b[1])

    def _quiet(self, now, point, speed):
        """Sessizlik sadece taze ve konumu kararli orneklerle ilerler."""
        if speed > self.settings.quiet_speed_cm_s:
            self._quiet_points = []
            return False
        if (self._quiet_points and self._distance(
                point, self._quiet_points[0][1]) > self.settings.baseline_radius_mm):
            self._quiet_points = []
        self._quiet_points.append((now, point))
        return now - self._quiet_points[0][0] >= self.settings.quiet_seconds

    def update(self, now, targets):
        """Yeni paketi isle; yalniz sayac arttiginda True dondur.

        Ayni okuma parcasindaki paketlerin zamanlari esit olabilir: bunlar
        sureyi/ardisik-ornek sayisini ilerletmez. Geriye giden zaman ise
        izlemeyi yeniden baslatir. Onceki sayimlar yeniden izlemede korunur.
        """
        if not isfinite(now):
            self._invalidate("Gecersiz zaman; yeniden kalibrasyon")
            self._last_time = None
            return False
        if self._last_time is not None:
            if now == self._last_time:
                return False
            if now < self._last_time:
                self._invalidate("Zaman geri gitti; yeniden kalibrasyon")
            elif now - self._last_time > self.settings.max_gap_seconds:
                self._invalidate("Veri araligi; yeniden kalibrasyon")
        self._last_time = now
        active = [target for target in targets if target.present]
        if len(active) != 1:
            self._invalidate("Hedef yok" if not active else "Birden fazla hedef")
            return False
        target = active[0]
        point = (target.x_mm, target.y_mm)
        speed = abs(target.speed_cm_s)
        if not all(isfinite(value) for value in (*point, speed)):
            self._invalidate("Gecersiz hedef verisi")
            return False
        if self._slot is not None and self._slot != target.slot:
            self._invalidate("Hedef yuvasi degisti; yeniden kalibrasyon")
        if (self._last_point is not None and self._distance(
                point, self._last_point) > self.settings.max_step_mm):
            self._invalidate("Konum sicramasi; yeniden kalibrasyon")
        self._slot = target.slot
        self._last_point = point

        if self._mode == "baseline":
            self.status = "Kalibrasyon: sabit durun"
            if speed > self.settings.quiet_speed_cm_s:
                self._baseline_points = []
                return False
            if (self._baseline_points and self._distance(
                    point, self._baseline_points[0][1]) > self.settings.baseline_radius_mm):
                self._baseline_points = []
            self._baseline_points.append((now, point))
            if (len(self._baseline_points) >= self.settings.baseline_samples
                    and now - self._baseline_points[0][0] >= self.settings.baseline_seconds):
                self._baseline = self._center(self._baseline_points)
                self._mode = "ready"
                self.ready = True
                self.status = "Hazir"
            return False

        if self._mode == "cooldown":
            self.status = "Bekleme: sabit durun"
            if (self._quiet(now, point, speed)
                    and now - self._last_count_time >= self.settings.cooldown_seconds):
                self._baseline = self._center(self._quiet_points)
                self._mode = "ready"
                self.ready = True
                self.status = "Hazir"
            return False

        if self._mode == "ready":
            if speed <= self.settings.quiet_speed_cm_s:
                return False
            self.ready = False
            self._mode = "burst"
            self._burst_started = now
            self._motion_streak = 0
            self._enough_motion = False
            self._peak_speed = 0.0
            self._peak_displacement = 0.0
            self._quiet_points = []

        self.status = "Hareket adayi; durulma bekleniyor"
        if now - self._burst_started > self.settings.max_burst_seconds:
            self._invalidate("Uzun hareket; yeniden kalibrasyon")
            return False
        self._motion_streak = (self._motion_streak + 1
                               if speed >= self.settings.motion_speed_cm_s else 0)
        self._enough_motion |= self._motion_streak >= self.settings.motion_samples
        self._peak_speed = max(self._peak_speed, speed)
        self._peak_displacement = max(
            self._peak_displacement, self._distance(point, self._baseline))
        if not self._quiet(now, point, speed):
            return False

        qualified = (self._enough_motion
                     and self._peak_displacement >= self.settings.displacement_mm
                     and now - self._last_count_time >= self.settings.cooldown_seconds)
        if qualified:
            self.count += 1
            self._last_count_time = now
            self.last_event = {
                "started_at_s": self._burst_started,
                "ended_at_s": now,
                "peak_speed_cm_s": self._peak_speed,
                "displacement_mm": self._peak_displacement,
            }
            self._mode = "cooldown"
            self.status = "Aday sayildi; bekleme"
            return True
        self._baseline = self._center(self._quiet_points)
        self._mode = "ready"
        self.ready = True
        self.status = "Hazir"
        return False
