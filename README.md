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