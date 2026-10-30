"""python -m radar --port COM5 --seconds 30 --label normal-jump"""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from .protocol import FrameParser, decode_frame


def positive(value):
    # Komut satırındaki süreyi doğrular; sıfır, negatif ve sonsuz süreyi reddeder.
    number = float(value)
    if not 0 < number < float("inf"):
        raise argparse.ArgumentTypeError("Sure pozitif ve sonlu olmali")
    return number


def live_chunks(port, baud, seconds):
    # PySerial yalnızca canlı okumada yüklenir; kayıt tekrarı donanım istemez.
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("PySerial gerekli: requirements-radar.txt dosyasina bakin") from exc
    # 8N1: 8 veri biti, eşlik biti yok, 1 dur biti; baud aktarım hızıdır.
    # Kısa okuma zaman aşımı, veri gelmese de süre kontrolüne dönmemizi sağlar.
    connection = serial.Serial(port=None, baudrate=baud, timeout=0.25,
                               bytesize=8, parity="N", stopbits=1)
    connection.port = port
    # Kontrol hatlarını kapalı tutarız; bu okuyucu radara ayar komutu göndermez.
    connection.dtr = False
    connection.rts = False
    try:
        connection.open()
        # Monoton saat geçen süre içindir; bilgisayar saati değişse de geriye gitmez.
        # UTC ise kaydın gerçek dünyada ne zaman alındığını belirtir.
        start = time.monotonic()
        while time.monotonic() - start < seconds:
            # Bir okuma parçası tek paket değildir: paketi bölebilir veya birkaçını içerebilir.
            # Baytları olduğu gibi döndürürüz; paket sınırlarını FrameParser bulur.
            chunk = connection.read(min(max(connection.in_waiting, 1), 4096))
            if chunk:
                yield {"elapsed_s": time.monotonic() - start,
                       "utc": datetime.now(timezone.utc).isoformat(),
                       "hex": chunk.hex()}
    finally:
        # Normal bitişte ve hata durumunda seri portu serbest bırakırız.
        connection.close()


def replay_chunks(path):
    # Önceki ham JSONL kaydı aynı çözümleme yoluna verilir; radara erişilmez.
    # Orijinal zamanlar korunur, ancak burada gerçek zamanlı bekleme yapılmaz.
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def main(argv=None):
    # Kullanıcı portu, kayıt süresini, deney etiketini ve çıktı klasörünü seçer.
    parser = argparse.ArgumentParser(description="LD2450 konum/hiz izleme ve kayit (ziplama karari vermez)")
    parser.add_argument("--port", default="COM5")
    parser.add_argument("--baud", type=int, default=256000)
    parser.add_argument("--seconds", type=positive, default=30)
    parser.add_argument("--label", default="unlabelled")
    parser.add_argument("--output", type=Path, default=Path("recordings/radar"))
    parser.add_argument("--replay", type=Path, help="Ham JSONL kaydini donanimsiz yeniden cozumle")
    parser.add_argument("--counter-window", action="store_true", help="Deneysel aday sayaci ve sureli deney penceresi")
    args = parser.parse_args(argv)
    if args.counter_window:
        # İsteğe bağlı pencere, yalnız radar kullanan süreli sayaç denemesini açar.
        # Tk arayüzünü bu dalda yüklemek, normal terminal kullanımını bağımsız tutar.
        if args.replay:
            parser.error("Pencere canli deney icindir; --replay ile birlikte kullanilamaz")
        from .window import main as window_main
        return window_main(args.port, args.baud, args.seconds, args.output)
    args.output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    # Ham JSONL özgün baytları, CSV ise çözümlenmiş ölçümleri saklar.
    # Böylece çözümleme değişse bile eski ham veriyi yeniden inceleyebiliriz.
    csv_path = args.output / (stamp + ".csv")
    raw_path = args.output / (stamp + ".jsonl")
    frame_parser = FrameParser()
    count = 0
    last_display = -1.0
    print(f"Etiket: {args.label} | {args.replay or args.port} | Sure: {args.seconds}s", flush=True)
    print("X/Y: radar duzleminde mm; hiz: cm/s. Y ziplama yuksekligi degildir.", flush=True)
    print(f"CSV: {csv_path}\nHam kayit: {raw_path}", flush=True)
    source = replay_chunks(args.replay) if args.replay else live_chunks(args.port, args.baud, args.seconds)
    try:
        with csv_path.open("x", newline="", encoding="utf-8") as csv_file, raw_path.open("x", encoding="utf-8") as raw_file:
            writer = csv.writer(csv_file)
            writer.writerow(["utc", "elapsed_s", "label", "frame", "slot", "present", "x_mm", "y_mm", "speed_cm_s", "resolution_mm"])
            for record in source:
                raw_file.write(json.dumps({**record, "label": args.label, "port": args.port, "baud": args.baud}) + "\n")
                # Çerçevenin zamanı son parçasının bilgisayarda okunma zamanıdır.
                # CSV boş yuvaları da yazar; hedef kaybolması kayıtta görünür kalır.
                for frame in frame_parser.feed(bytes.fromhex(record["hex"])):
                    count += 1
                    targets = decode_frame(frame)
                    for t in targets:
                        writer.writerow([record["utc"], record["elapsed_s"], args.label, count,
                                         t.slot, int(t.present), t.x_mm, t.y_mm, t.speed_cm_s, t.resolution_mm])
                    # Ekranı yarım saniyede bir yenileriz; kayıt tüm paketleri içerir.
                    if record["elapsed_s"] - last_display >= 0.5:
                        active = [f"#{t.slot} X={t.x_mm} Y={t.y_mm} hiz={t.speed_cm_s}" for t in targets if t.present]
                        print(f"{record['elapsed_s']:6.1f}s | " + (" | ".join(active) or "Hedef yok"), flush=True)
                        last_display = record["elapsed_s"]
    # Ctrl+C ölçümü bitirir; port/dosya hataları başarısız çıkış koduyla bildirilir.
    except KeyboardInterrupt:
        print("\nOlcum durduruldu; alinan kayitlar korundu.")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Radar okunamadi: {exc}")
        return 1
    finally:
        source.close()
    print(f"Paket: {count} | Atilan bayt: {frame_parser.discarded_bytes} | Eksik kalan bayt: {len(frame_parser.buffer)}")
    if not count:
        # Portun açılması tek başına başarı değildir; geçerli paket de alınmalıdır.
        print("Gecerli paket yok; port, besleme, TX-RX ve baud ayarini kontrol edin.")
        return 2
    return 0


if __name__ == "__main__":
    # Modülü içe aktarmak ölçümü başlatmaz; yalnız doğrudan çalıştırmada başlar.
    raise SystemExit(main())
