# Jump Detection — Python

Python, OpenCV ve MediaPipe kullanılarak geliştirilmiş gerçek zamanlı zıplama algılama prototipi.

## Özellikler

- Web kamerasıyla canlı görüntü alma
- MediaPipe ile insan vücudu takibi
- Otomatik 3 saniyelik kalibrasyon
- Omuz ve kalça hareketlerinden zıplama tespiti
- Zıplama sayacı
- Hareket hızı ve yükselme analizi

## Kullanılan Teknolojiler

- Python 3.12
- OpenCV
- MediaPipe
- NumPy

## Çalıştırma

```bash
pip install opencv-python mediapipe
python main.py
```

Çalıştırmadan önce `pose_landmarker_lite.task` model dosyasının proje klasörüne indirilmesi gerekir.

## Kontroller

- **Q:** Programı kapat
- **R:** Kalibrasyonu ve sayacı sıfırla

## Bilinen Sınırlamalar

Kamera ayakları görmediğinde parmak ucuna yükselme hareketi yanlışlıkla zıplama olarak algılanabilir.

## Proje Durumu

Geliştirme aşamasındadır. Gelecekte radar entegrasyonu planlanmaktadır.

## Modüler yapı

- `main.py`: Mevcut `python main.py` komutunun giriş noktası.
- `jump_detection/app.py`: Kamera, MediaPipe ve OpenCV ekran döngüsü.
- `jump_detection/config.py`: Model yolu, eşikler ve çizim bağlantıları.
- `jump_detection/features.py`: Omuz ve kalça noktalarından gövde Y hesabı.
- `jump_detection/detector.py`: Kalibrasyon, hız, sayaç ve yeniden hazır olma kuralları.
- `tests/`: Kamera, model veya üçüncü taraf paket gerektirmeyen kontroller.

Modülleri içe aktarmak kamerayı açmaz. Kamera uygulaması mevcut Windows DirectShow arka ucunu (`CAP_DSHOW`) kullanmaya devam eder.

## Model dosyası

`pose_landmarker_lite.task` bilinçli olarak Git dışında tutulur; depoyu klonlamak bu dosyayı indirmez. Mevcut çalışan dosyanızı veya [Google'ın Pose Landmarker Lite modelini](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task) proje köküne, `main.py` ile aynı klasöre yerleştirin.

Model yolu artık komutu çalıştırdığınız klasörden bağımsızdır. Dosya yoksa kamera açılmadan açıklayıcı hata gösterilir. Donanımsız testler için model indirmek gerekmez.

## Donanımsız doğrulama

Python 3.12 ile proje kökünden:

```bash
python -m compileall -q main.py jump_detection tests
python -m unittest discover -s tests -v
```

GitHub Actions aynı kontrolleri çalıştırır. Bu kontroller kalibrasyon, eşikler, tek sayım, bekleme süresi, yeniden hazır olma, takip kaybından sonra hız geçmişi, sıfırlama ve başlangıç davranışını kapsar. Gerçek kamera, model çıkarımı, kurulu OpenCV/MediaPipe uyumu veya radar bağlantısını doğrulamaz.

`requirements.txt` önceki ortamın sürüm listesidir; bu düzenlemede değiştirilmemiştir. Hem `opencv-python` hem `opencv-contrib-python` içerdiğinden temiz kurulum ve bağımlılık sadeleştirmesi ayrıca doğrulanmalıdır. Mevcut çalışan ortamı değiştirmeden önce ayrı bir sanal ortam kullanın.

## Korunan davranış ve sonraki adımlar

Bu düzenleme algılama eşiklerini değiştirmez. Yükselme görüntü yüksekliğine göre normalize koordinat, hız ise bu koordinat/saniye cinsindedir; santimetre ölçümü değildir. Mevcut karar ayak temasını denetlemediği için ayaklar görünse bile parmak ucuna yükselme yanlış pozitif oluşturabilir.

Geliştirme ve elle doğrulama sırası için [geliştirme planına](docs/development-plan.md) bakın. Radar okuyucu ve Unity bağlantısı henüz uygulanmamıştır.
