# Geliştirme planı ve doğrulama sınırları

## 5 Kasım 2026 güncellemesi

Unity 6000.6.7f1 projesi, hesap/sonuç API ve SQL şeması hazırlandı. Klavye, simülasyon ve deneysel radar aktarımı denendi. Yeni ana menü ve saydam giriş/HUD eklendi. Ayrıntılar: [güncel çalışma özeti](2026-11-05-progress.md). Aşağıdaki takvim ilk plandır; bazı işler öne alındı.

## 2-8 Kasım 2026: ilk plan

**Gösterilecek çıktı:** Unity'de tek bir deneme sahnesi; zemin, karakter, bir
engel, bitiş ve yeniden başlatma. Önce klavyeyle oynanır, sonra aynı zıplama
isteğinin Python simülasyonundan gelişi denenir. Deneysel radar girdisi ayrı
seçilir. Bu sahne, radarın fiziksel zıplamayı doğru ayırdığının kanıtı değildir.

Kullanıcının proje takvimindeki sıralama korunur: M3 UART okuma 6 Kasım'a,
M4 radar analizi 13 Kasım'a kadar; M5 Unity oyunu 7-20 Kasım, M6 radar–Unity
entegrasyonu 14-27 Kasım. Bu haftaki küçük olay aktarımı M6 için hazırlıktır.
M7 UML/veritabanı tasarımının hedef tarihi 13 Kasım'dır.

| Gün | Yapılacak iş | Elle tutulur çıktı / tamamlanma ölçütü |
| --- | --- | --- |
| 2 Kasım | Unity Hub ve Unity 6 LTS kurulumu; olay sözleşmesi ve yerel köprü hazırlığı | Unity Editor açılır; donanımsız gönderici/alıcı denemesi geçer |
| 3-4 Kasım | Radar v2 ile aynı yerleşimde normal/hafif zıplama ve yürüyüş/sabit duruş denemeleri | Her denemede gerçek adet, radar adayı, sürüm ve takip kapsamı ayrı kaydedilir |
| 5 Kasım | Sonuçları inceleme; mevcut sınıfların UML taslağıyla eşleştirilmesi | Kaçırma/yanlış tetikleme örnekleri ve sınıfların sorumlulukları yazılır |
| 6 Kasım | M3 UART okuma çıktısını ve M4'te kalan sorunları özetleme | Geçerli paket örneği, ham kayıt ve kısa sonuç tablosu gösterilir |
| 7-8 Kasım | Unity 2D deneme sahnesini açma; klavye ve simülasyonla oynama | Karakter zıplar, havadayken ikinci zıplama engellenir, engel/bitiş ve yeniden başlatma denenir |

Radar analizi bu hafta da sürer. Yürümede beklenen **gerçek zıplama sayısı
0**'dır; yürüme turu sayısı bu alana girilmez. Toplam aday ve gerçek adet
eşitliği tek başına doğru algılama oranı değildir; olayların hangi harekete
denk geldiğini de incelemek gerekir. Deneme sonucu iyileştirilmiş gibi
görünsün diye eşikler gerçek adede uydurulmaz.

## Güncel uygulama durumu

- Kamera prototipi ve bağımsız radar okuma/kayıt/deney penceresi var.
- Radarın v2 sayacı arka arkaya hareketler için yerelde düzenlendi; fiziksel
  doğrulaması tamamlanmış sayılmıyor. Radar hâlâ hareket adayları üretiyor.
- `game_bridge/` yerel UDP olay gönderici, simülasyon ve tanı alıcısını içerir.
  Ek Python paketi veya radar gerektirmez.
- Radar penceresindeki `--game-events` seçeneği yalnız aktif deneyde sayılan
  adayları oyuna zıplama isteği olarak gönderir. Hazırlık ve her ölçüm paketi
  oyun olayı üretmez. Deneme bitince gönderim de durur.
- Çalışan Unity kaynakları `unity/RadarPlatformGame/Assets/Scripts` içindedir. Bir oynanabilir bölüm, menü/giriş ve sonuç ekranları vardır.
- Kamera, radarın karşılaştırma/destek kaynağıdır; bu ilk oyun bağlantısında
  kamera olayları henüz aktarılmıyor. ASP.NET Core API ve SQL Server hesap/ilerleme sistemi uygulanmıştır.

Kurulum ve ilk oyun denemesi: [Unity yönergeleri](../unity/README.md).
Olayın anlamı ve deneme komutları: [oyun girdisi sözleşmesi](game-input-contract.md).
5 Kasım yayını için kullanıcı GitHub gönderimini ve `main` birleşimini açıkça onayladı.

## Bu düzenlemenin kapsamı

Mevcut kamera prototipi küçük modüllere ayrıldı. Kalibrasyon süresi (3.0), yükselme (0.055), hız (0.12), bekleme (0.65) ve dönüş (0.025) eşikleri korundu. Ekran metinleri, sayaç, görünürlük kontrolleri ve R/Q tuşları korunuyor.

Başlangıçtaki model yolu proje köküne bağlandı. Modül içe aktarılırken kamera açılmıyor. Model dosyası Git dışında kalıyor.

Donanımsız kontrollerin başarı durumu GitHub Actions üzerinden görülmelidir. Kamera ile davranış eşdeğerliği, MediaPipe/OpenCV kurulumu ve fiziksel radar çalışması bu testlerden çıkarılamaz.

## Kamerada elle karşılaştırma

Aynı model, kamera konumu, ışık, kişi ve çalışan Python ortamıyla önceki sürümle yeni dal karşılaştırılmalı:

1. Hareketsiz duruşta kalibrasyonun ve sayacın kontrolü.
2. Normal ve hafif zıplamalar.
3. Tek harekette çift sayım olmaması ve inişten sonra yeniden hazır olma.
4. Yavaş/hızlı parmak ucuna yükselme: mevcut yanlış pozitifler kaydedilmeli; çözülmüş sayılmamalı.
5. Omuz veya kalça görünürlüğünün kaybolup geri gelmesi.
6. R ile kalibrasyon/sayaç sıfırlama; Q ile çıkış ve kamera kaynağının bırakılması.

## Algılamayı iyileştirme

Önce zaman damgalı gövde konumu, görünürlük, hız, yükselme ve karar kaydı eklenmeli. Normal/hafif zıplama, parmak ucuna yükselme, çömelme, yürüme ve takip kaybı etiketlenmeli.

Sonra kararlı kalibrasyon, zaman tabanlı hız penceresi ve takip kaybından dönüş ayrı değişikliklerde ele alınmalı. Ayak bileği (27–28), topuk (29–30) ve ayak ucu (31–32) özellikleri aday doğrulamasında denenebilir. Görüntü koordinatları kesin zemin teması veya metrik zıplama yüksekliği sağlamaz. Ayaklar görünmediğinde belirsizlik ayrıca ele alınmalı.

Yeni yöntem mevcut yöntemle aynı kayıtlar üzerinde karşılaştırılmalı. Yanlış pozitif, kaçırılan hafif zıplama, çift sayım ve oyun kontrolünü etkileyen gecikme birlikte ölçülmeli.

## Radar için bağımsız modül

İlk aşamadaki ham bayt kaydı ve protokol çözümleme uygulandı. Gerçekleşen
dosya dağılımı şöyledir:

- `radar/__main__.py`: Yapılandırılabilir port/baud/zaman aşımı, terminal kaydı ve tekrar oynatma. COM5 yerel bir ayardır.
- `radar/protocol.py`: Üretici belgesine göre tamponlama, çerçeve sınırları, alan kodlaması, birimler ve bozuk veriden toparlanma.
- `radar/trial.py`: Deney saati, ham baytlar, ölçümler, adaylar ve gerçek adedin ayrı kaydı.
- `radar/counter.py`: Deneysel hareket adayı kuralları.
- `radar/window.py`: Süreli deney arayüzü ve isteğe bağlı oyun olayı gönderimi.
- Çevrimdışı tekrar oynatma ve eksik/birleşik/bozuk paket testleri var.

PySerial bağımlılığı `requirements-radar.txt` içindedir. Mevcut bilgisayarda
radar için PySerial kurulu sistem Python'u, kamera için mevcut `.venv`
kullanılır. Çalışan ortamlar değiştirilmez. Dönüştürücünün COM5 olarak
tanınması tek başına radarın veri ürettiğini doğrulamaz; geçerli paket
okunması ve hedef alanları ayrıca kontrol edilir.

LD2450 X/Y konumu ve hız alanları doğrudan dikey zıplama yüksekliği değildir. Montaj, koordinat sistemi, örnekleme davranışı ve gerçek hareket kayıtları incelenmeden radarın zıplamayı tek başına ayırabildiği varsayılmamalı.

## Unity ve sunucu

Python–Unity olay sözleşmesinin ilk sürümü yerel UDP/JSON'dur. `jump_request`
oyunun zıplama isteğidir; radar kaynağında `motion_candidate` kanıt etiketi
korunur. Oyun yalnız seçilen kaynağı dinler; önce simülasyonla bağlantı,
sonra deneysel radar girdisi denenir. Sürekli oyun oturumu, gecikme ölçümü
ve radarın yanlış tetikleme kontrolü M6'nın tamamlanma koşullarıdır.
Kamera karşılaştırma/destek kaynağı olarak tutulur. ASP.NET Core API ve SQL Server altyapısı uygulanmıştır; üretim dağıtımı henüz yapılmadı.
