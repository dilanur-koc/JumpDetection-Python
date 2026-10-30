"""Kamera kullanmadan baslatilan, sure sonunda duran deney penceresi."""

import math
from pathlib import Path
import time
import tkinter as tk
from tkinter import messagebox, ttk

from .counter import CounterSettings, ExperimentalCounter
from .protocol import FrameParser, decode_frame
from .trial import TrialClock, TrialRecorder


# Bunlar seçilebilir deney adları, kayıt etiketleri ve kullanıcı yönergeleridir.
# Ayrı hareket tanıyıcıları değildir; bütün seçeneklerde aynı deneysel sayaç çalışır.
EXPERIMENTS = {
    "Normal zıplama": ("normal-jump", "Aralarda bekleyerek tam 5 kez zıpla, sonra dur."),
    "Hafif zıplama": ("light-jump", "Aralarda bekleyerek tam 5 hafif zıplama yap, sonra dur."),
    "Yürüme": ("walking", "Zıplamadan yürü; sayaç artıyor mu kontrol edeceğiz."),
    "Parmak ucuna yükselme": ("tiptoe", "Zıplamadan, aralarda bekleyerek parmak ucuna yüksel."),
    "Çömelme": ("squat", "Zıplamadan, aralarda bekleyerek çömelip doğrul."),
    "Sabit duruş": ("standing", "Deneme boyunca hareketsiz dur."),
}


class RadarWindow:
    def __init__(self, root, port="COM5", baud=256000, duration=20, output=Path("recordings/radar")):
        self.root, self.port, self.baud = root, port, baud
        self.duration, self.output = duration, output
        self.connection = None
        self.recorder = None
        # İşleri ayır: clock süreyi, counter aday sayımını, parser paketleri yönetir.
        self.clock = TrialClock(duration=duration)
        self.counter = ExperimentalCounter()
        self.parser = FrameParser()
        self.after_id = None
        self.last_frame = None
        self.reported_error = None
        # Burada pencereyi oluşturuyoruz. Seri port Başlat'a basılana kadar açılmaz.
        root.title("Radar denemesi — deneysel sayaç")
        root.geometry("740x640")
        root.minsize(650, 610)
        root.protocol("WM_DELETE_WINDOW", self.close)
        body = ttk.Frame(root, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Yalnızca radar · Kamera kullanılmıyor", font=("Segoe UI", 15, "bold")).pack()
        self.banner = tk.Label(body, text="HAZIR — Başlat düğmesine bas", font=("Segoe UI", 20, "bold"), fg="#174566")
        self.banner.pack(pady=(18, 6))
        self.timer = ttk.Label(body, text=f"5 sn hazırlık + {duration:g} sn deneme", font=("Segoe UI", 15))
        self.timer.pack()
        self.count_label = ttk.Label(body, text="0", font=("Segoe UI", 66, "bold"))
        self.count_label.pack()
        ttk.Label(body, text="Zıplama adayı · deneysel hareket sayımı", font=("Segoe UI", 12)).pack()
        ttk.Label(body, text="Bu sayı henüz doğrulanmış zıplama sayısı değildir.").pack(pady=(3, 12))
        self.mode = tk.StringVar(value="Normal zıplama")
        self.mode_box = ttk.Combobox(body, textvariable=self.mode, values=list(EXPERIMENTS), state="readonly", width=30)
        self.mode_box.pack()
        self.instruction = ttk.Label(body, text="Radarı sabitle. Anten yüzü sana baksın; karşısında tek kişi olsun.", wraplength=650, justify="center")
        self.instruction.pack(pady=10)
        self.telemetry = ttk.Label(body, text=f"{port} · Başlatılmadı", wraplength=650)
        self.telemetry.pack(pady=5)
        self.status = ttk.Label(body, text="Önce varsa kamera penceresini Q ile kapat.", wraplength=650)
        self.status.pack()
        buttons = ttk.Frame(body)
        buttons.pack(pady=12)
        self.start_button = ttk.Button(buttons, text="Başlat", command=self.start)
        self.start_button.pack(side="left", padx=8)
        self.stop_button = ttk.Button(buttons, text="Durdur", command=lambda: self.finish("stopped"), state="disabled")
        self.stop_button.pack(side="left", padx=8)
        # Gerçek sayı kullanıcı tarafından girilir; otomatik olarak 5 kabul edilmez.
        actual = ttk.Frame(body)
        actual.pack()
        ttk.Label(actual, text="Gerçekte kaç kez zıpladın?").pack(side="left")
        self.actual = ttk.Entry(actual, width=5)
        self.actual.pack(side="left", padx=8)
        self.save_button = ttk.Button(actual, text="Sonucu kaydet", command=self.save_actual, state="disabled")
        self.save_button.pack(side="left")
        self.saved = ttk.Label(body, text="Kayıtlar: recordings/radar", wraplength=650, justify="center")
        self.saved.pack(pady=12)

    def start(self):
        # Önceki denemenin sayısını ve hata bilgisini yeni denemeye taşıma.
        self.recorder = None
        self.counter = ExperimentalCounter(CounterSettings())
        self.reported_error = None
        try:
            import serial
            # timeout=0 okumayı bekletmez; pencerenin düğmeleri ve saati çalışır.
            # Baud ve 8N1 ayarları radarın veri çıkışıyla eşleşmelidir.
            self.connection = serial.Serial(port=None, baudrate=self.baud, timeout=0,
                                            bytesize=8, parity="N", stopbits=1)
            self.connection.port = self.port
            self.connection.dtr = False
            self.connection.rts = False
            self.connection.open()
            self.parser = FrameParser()
            # Seçim, kaydın hangi deney türüne ait olduğunu belirtir.
            label, instruction = EXPERIMENTS[self.mode.get()]
            self.recorder = TrialRecorder(self.output, label, self.counter.settings,
                                          self.port, self.baud, self.duration)
            self.started_at = time.monotonic()
            self.clock = TrialClock(duration=self.duration)
            self.clock.start(self.started_at)
            self.last_frame = None
            self.reported_error = None
            self.active_announced = False
            self.actual.delete(0, "end")
            self.count_label.config(text="0")
            self.instruction.config(text="Şimdi sabit dur. BAŞLA yazısını bekle.\n" + instruction)
            # Deney sürerken yeniden Başlat'a basılmasını ve deney türünün
            # değiştirilmesini engelle; Durdur düğmesi kullanılabilir kalsın.
            self.start_button.config(state="disabled")
            self.mode_box.config(state="disabled")
            self.stop_button.config(state="normal")
            self.save_button.config(state="disabled")
            self.saved.config(text="Ham veri, ölçümler ve sayaç olayları kaydediliyor.")
            self.poll()
        except (ImportError, OSError, ValueError) as exc:
            self.reported_error = str(exc)
            self.finish("error")
            self.status.config(text=f"Port açılamadı: {exc}")

    def poll(self):
        # Tkinter bu kısa kontrolü yaklaşık her 30 ms'de tekrar çağırır.
        # Uzun bir while döngüsü kullanmadığımız için pencere donmadan güncellenir.
        self.after_id = None
        try:
            now = time.monotonic()
            # Veri kesilirse eski hedefi kullanma. Deney saati yeni paket gelmesini
            # beklemediğinden bağlantı koptuğunda da süre sonunda durabiliriz.
            if self.last_frame is None or now - self.last_frame > 0.4:
                self.counter.update(now - self.started_at, [])
            previous_phase = self.clock.phase
            phase = self.clock.advance(now, self.counter.ready)
            if phase in ("done", "no_baseline"):
                self.finish(phase)
                return
            if phase == "active" and previous_phase != "active":
                # Hazırlıkta görülen hareketler aktif deneyin sayımına eklenmesin.
                self.counter.begin_trial()
                self.recorder.summary["active_started_elapsed_s"] = now - self.started_at
            waiting = self.connection.in_waiting
            if waiting:
                # Her okumada sınırlı veri al. Bir okumada eksik veya birden çok
                # paket olabilir; parser bunları ayırıp tamamlanmış paketleri verir.
                data = self.connection.read(min(waiting, 4096))
                elapsed = now - self.started_at
                record = self.recorder.chunk(elapsed, data, phase)
                for frame in self.parser.feed(data):
                    targets = decode_frame(frame)
                    self.last_frame = now
                    detected = self.counter.update(elapsed, targets)
                    # Ham ölçümleri hazırlıkta da saklarız; aday olayları ve görünen
                    # sayaç yalnızca aktif deney aşamasında kayda/geçerli sayıya girer.
                    if phase == "active" and detected:
                        self.recorder.event(record, self.counter.count, getattr(self.counter, "last_event", None))
                    self.recorder.frame(record, targets, self.counter.count if phase == "active" else 0, self.counter.status)
                    active = [f"#{t.slot}: X {t.x_mm} mm · Y {t.y_mm} mm · hız {t.speed_cm_s} cm/sn" for t in targets if t.present]
                    self.telemetry.config(text=" | ".join(active) or "Hedef yok")
            if self.last_frame is None or now - self.last_frame > 0.4:
                self.counter.update(now - self.started_at, [])
                self.telemetry.config(text="Veri yok / paketler kesildi")
            self.count_label.config(text=str(self.counter.count) if phase == "active" else "0")
            # Hazırlık ve aktif deney için kullanıcıya farklı renk/yönerge göster.
            if phase == "prepare":
                remaining = math.ceil(self.clock.remaining(now))
                self.banner.config(text="SABİT DUR — Hazırlanıyor", fg="#996000")
                self.timer.config(text=f"Başlamadan önce: {remaining} sn" if remaining else "Tek, sabit hedef bekleniyor…")
            else:
                if not getattr(self, "active_announced", False):
                    self.beep()
                    self.active_announced = True
                self.banner.config(text="BAŞLA — Deneme sürüyor", fg="#06703d")
                self.timer.config(text=f"Kalan süre: {math.ceil(self.clock.remaining(now))} sn")
                self.instruction.config(text=EXPERIMENTS[self.mode.get()][1])
            self.status.config(text=f"{self.counter.status} · Y, dikey zıplama yüksekliği değildir.")
            self.after_id = self.root.after(30, self.poll)
        except (OSError, ValueError) as exc:
            self.reported_error = str(exc)
            self.finish("error")
            self.status.config(text=f"Okuma hatası: {exc}")

    def finish(self, reason):
        # Düğme, süre sonu, hata veya pencerenin kapanması bu ortak temizliği kullanır.
        cleanup_errors = []
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError as exc:
                cleanup_errors.append(str(exc))
            self.after_id = None
        if self.connection is not None:
            # Seri portu bırak; sonraki deney veya başka uygulama yeniden açabilsin.
            try:
                self.connection.close()
            except OSError as exc:
                cleanup_errors.append(f"Port kapatma: {exc}")
            finally:
                self.connection = None
        if self.clock.active_at is None:
            # Deney başlayamadıysa hazırlıktaki olası adayları sonuç diye gösterme.
            self.counter.count = 0
        self.clock.phase = reason
        self.active_announced = False
        if self.recorder is not None and self.recorder.summary["finish_reason"] == "in_progress":
            self.recorder.summary["active_duration_s"] = (max(0.0, time.monotonic() - self.clock.active_at)
                                                          if self.clock.active_at is not None else 0.0)
            if self.reported_error:
                self.recorder.summary["error"] = self.reported_error
            try:
                # Bir kaydetme hatası olsa da düğmeleri tekrar kullanılabilir yap.
                self.recorder.finish(reason, self.counter.count, self.parser.discarded_bytes, len(self.parser.buffer))
            except OSError as exc:
                cleanup_errors.append(f"Kayıt tamamlanamadı: {exc}")
                self.saved.config(text="Kayıt hatası — dosyalar eksik olabilir.")
            else:
                self.save_button.config(state="normal")
                self.saved.config(text=f"Kayıt: {self.recorder.summary_path}")
        titles = {"done": "BİTTİ — DUR", "stopped": "DURDURULDU", "no_baseline": "BAŞLAMADI — Sabit hedef bulunamadı", "error": "DENEME BAŞARISIZ"}
        self.banner.config(text=titles.get(reason, "DURDURULDU"), fg="#a52020")
        self.timer.config(text="Sayım durdu. Sonuç aşağıda sabit kalır.")
        if self.recorder is not None:
            frames = self.recorder.summary["active_frames"]
            tracked = self.recorder.summary["single_target_active_frames"]
            self.status.config(text=f"Tek hedef görülen ölçüm: {tracked}/{frames}. Yalnızca aday sayımıdır.")
        if cleanup_errors:
            self.status.config(text=" | ".join(cleanup_errors))
        self.instruction.config(text="Artık zıplama. Gerçek zıplama sayını yazıp Sonucu kaydet düğmesine bas.")
        # Sonuç penceresi açık kalır ama yeni okumalar planlanmadığı için sayı donar.
        self.count_label.config(text=str(self.counter.count))
        self.start_button.config(state="normal")
        self.mode_box.config(state="readonly")
        self.stop_button.config(state="disabled")
        self.beep()

    def save_actual(self):
        # Kullanıcının saydığı gerçek adet ile radarın aday adedini ayrı kaydet.
        try:
            self.recorder.report_actual(int(self.actual.get()))
        except (ValueError, OSError) as exc:
            messagebox.showerror("Sonuç kaydedilemedi", str(exc), parent=self.root)
            return
        self.status.config(text=f"Gerçek sayı: {self.actual.get()} · Radar adayı: {self.counter.count} · Kaydedildi")

    def beep(self):
        self.root.bell()

    def close(self):
        # Sağ üstteki X'e basılması da portu ve varsa devam eden kaydı kapatır.
        try:
            if self.connection is not None:
                self.finish("window_closed")
        finally:
            self.root.destroy()


def main(port="COM5", baud=256000, duration=20, output=Path("recordings/radar")):
    # mainloop pencere olaylarını işler; RadarWindow yalnızca radar kullanır.
    root = tk.Tk()
    RadarWindow(root, port, baud, duration, output)
    root.mainloop()
    return 0
