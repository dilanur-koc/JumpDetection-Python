# Jump Detection — Python

## Radar denemesi (LD2450)

Kamera uygulamasi `python main.py` olarak kalir. Radar bagimsiz calisir:

### Deneysel radar sayaci penceresi

```powershell
python -m radar --counter-window --port COM5 --seconds 20
```

Kamera acilmaz. Penceredeki **Baslat** dugmesine basin; 5 saniye sabit durun.
Tek ve sabit hedef kalibrasyonu tamamlaninca **BASLA** gorunur ve ses duyulur.
Tam 5 ziplama yapin, aralarda yaklasik 3 saniye bekleyin. **BITTI — DUR**
gorununce hareketi bitirin: sayac donar, port kapanir, sonuc penceresi acik
kalir. Gercek ziplama adedini kendiniz girip **Sonucu kaydet** dugmesine basin.
Bu sayi otomatik olarak 5 varsayilmaz. Yurumede gercek ziplama adedi 0'dir.
Hazirlikta 20 saniye icinde kararli tek hedef yoksa deney baslamaz.

Bu arac **deneysel hareket adaylarini** sayar; fiziksel ziplama dogrulamasi
degildir. Ilk deneme esikleri: en az iki taze olcumde 16 cm/sn hiz,
60 mm duzlemsel konum degisimi ve en az 0.25 sn durulma; ardindan 0.6 sn
bekleme. Hazirlik kalibrasyonu en az 1 sn surer. Ayarlar `radar/counter.py`
icindeki `CounterSettings` ile tanimlanir ve her denemenin ozetine kaydedilir.
Esikler bir denemenin sonucunu 5'e esitlemek icin secilmemistir.
Yurume/comelme de aday sayilabilir; kisa bir yurume + durma hareketinin
sayilabildigi testlerle acikca belgelenmistir. 0 sonucu da mumkundur.
Yuva degisimi, birden fazla hedef, veri kaybi ve buyuk konum sicramasi
bekleyen adayi iptal eder. Sayac bu kontrollerle ayni harekette tekrar
sayimi sinirlar; kesin kisi takibi veya ziplama siniflandirmasi saglamaz.

Pencere ham JSONL, olcum CSV, aday olaylari ve `.summary.json` dosyasi saklar.
Ozet gercek sayiyi, radar aday sayisini, ayarlari ve tek hedef gorulen aktif
olcum sayisini ayri tutar. Bu kayitlar disinda daha onceki etiketli ama
kesin ziplama zamanlari bilinmeyen kayitlardan basarim orani cikarilmamalidir.

### Sadece veri izleme ve kayit

```powershell
python -m pip install -r requirements-radar.txt
python -m radar --port COM5 --seconds 30 --label standing
python -m radar --port COM5 --seconds 30 --label walking
python -m radar --port COM5 --seconds 30 --label normal-jump
python -m radar --port COM5 --seconds 30 --label light-jump
python -m radar --port COM5 --seconds 30 --label tiptoe
python -m radar --port COM5 --seconds 30 --label squat
```

PySerial kurulu bir yorumlayici kullanin; mevcut kamera `.venv` ortamini
degistirmek gerekmez. Her komut ayri deneydir: radar sabit kalsin, tek kisi
olsun ve sadece belirtilen hareket yapilsin. Etiket deneyin adidir; otomatik
hareket siniflandirmasi degildir. Ctrl+C ile durdurulabilir. COM portunu
ayni anda baska bir uygulama acmamali.

Kayitlar `recordings/radar/` altinda CSV ve ham JSONL olarak olusur ve Git'e
eklenmez. CSV, bos hedef yuvalari dahil her pakette uc satir saklar.
`slot` kalici kisi kimligi degildir. Zaman damgalari bilgisayarin okuma
zamanidir; parcalanmis pakette son parcaya aittir. Ham kayit yeniden cozumlenebilir:

```powershell
python -m radar --replay recordings/radar/KAYIT.jsonl --label normal-jump
```

X/Y radar duzleminde milimetre, hiz cm/s, mesafe cozunurlugu milimetredir.
Y dikey ziplama yuksekligi degildir. Salt veri izleme komutu ziplama saymaz ve radara ayar
komutu gondermez. Baslik/son isaretleri dogrulanir; bu raporlarda checksum
olmadigindan tum veri bozulmalarinin yakalanmasi garanti edilmez.
Sifir paket ve port hatalari basarisiz cikis koduyla bildirilir.

Protokol kaynagi: [Hi-Link LD2450 kullanim kilavuzu, bolum 6](https://r0.hlktech.com/download/HLK-LD2450-24G/1/HLK%20LD2450%201T2R%E8%BF%90%E5%8A%A8%E7%9B%AE%E6%A0%87%E6%A3%80%E6%B5%8B%E8%BF%BD%E8%B8%AA%E6%A8%A1%E7%BB%84%E8%AF%B4%E6%98%8E%E4%B9%A6%20V1.01.pdf).

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
