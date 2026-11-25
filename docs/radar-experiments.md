# LD2450 — Deneysel radar çalışmaları

Bu belge radar deneylerinin ayrıntılarını ve önceki ayar notlarını korur.
Güncel kamera ile oyun gösterimi için [ana sayfayı](../README.md) ve
[25 Kasım sunum rehberini](2026-11-25-demo-guide.md) kullanın.
Komutlar depo kökünden çalıştırılır.

## Radar denemesi (LD2450)

Kamera uygulamasi `python main.py` olarak kalir. Radar bagimsiz calisir:

### Deneysel radar sayaci penceresi

```powershell
& "C:\Users\Dila\AppData\Local\Programs\Python\Python312\python.exe" -m radar --counter-window --port COM5 --seconds 20
```

Kamera acilmaz. Penceredeki **Baslat** dugmesine basin; 5 saniye sabit durun.
Tek ve sabit hedef kalibrasyonu tamamlaninca **BASLA** gorunur ve ses duyulur.
Kendi ritminizde tam 5 ziplama yapin; sonrasinda durun. Iki ziplama arasinda
iki saniye bekleme kurali yoktur. **BITTI — DUR**
gorununce hareketi bitirin: sayac donar, port kapanir, sonuc penceresi acik
kalir. Gercek ziplama adedini kendiniz girip **Sonucu kaydet** dugmesine basin.
Bu sayi otomatik olarak 5 varsayilmaz. Yurumede gercek ziplama adedi 0'dir.
Hazirlikta 20 saniye icinde kararli tek hedef yoksa deney baslamaz.

Bu arac **deneysel hareket adaylarini** sayar; fiziksel ziplama dogrulamasi
degildir. Hassas deneme esikleri: en az iki taze olcumde 12 cm/sn hiz,
30 mm duzlemsel konum degisimi ve en az 0.1 sn/iki taze ornek durulma;
sayimlar arasinda en az 0.25 sn bekleme. Bu sureler durulma ve hareket
kosullarini kaldirmaz; sure dolmasi tek basina sayim olusturmaz.
Hazirlik kalibrasyonu en az 1 sn surer. Ayarlar `radar/counter.py`
icindeki `CounterSettings` ile tanimlanir ve her denemenin ozetine kaydedilir.
Esikler bir denemenin sonucunu 5'e esitlemek icin secilmemistir.
Yurume/comelme de aday sayilabilir; kisa bir yurume + durma hareketinin
sayilabildigi testlerle acikca belgelenmistir. 0 sonucu da mumkundur.
Yuva degisimi, birden fazla hedef, veri kaybi ve buyuk konum sicramasi
bekleyen adayi iptal eder. Sayac bu kontrollerle ayni harekette tekrar
sayimi sinirlar; kesin kisi takibi veya ziplama siniflandirmasi saglamaz.

`max_burst_seconds=2.0`, iki ziplama arasindaki bekleme degil, tek hareket
adayinin tamamlanma siniridir. Uzayan aday sayilmadan iptal edilir; hedef
takibi suruyorsa kisa durulmadan sonra yeni aday degerlendirilebilir.
Hedef gercekten kaybolursa yine baslangic kalibrasyonu gerekir.
6 Kasim'da kullanici istegiyle hiz 16'dan 12 cm/sn'ye, duzlemsel yer
degistirme 60'tan 30 mm'ye indirildi. Sure ve taze ornek kontrolleri korundu.
Yeni denemelerin ozetinde `counter_version=burst-quiet-v6-demo-confirmation` saklanir.
Onceki v1/v2 kayitlari eski ayarlar ve sonuclariyla korunur. Daha dusuk esikler
kucuk hareketleri denemek icindir; fiziksel ziplama dogrulugu saglamaz ve
yurumede yanlis sayimi artirabilir. Acik radar penceresi yeni kodu almaz;
degisiklikten sonra pencereyi kapatip ayni komutla yeniden baslatin.

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

### Radar oyun alanı

Uzakta raporlanan ek hedefler tek kişilik sayacı yeniden kalibrasyona döndürebilir.
Sayaç penceresindeki **Oyun alanı (mm)** ile yalnız oyuncunun alanını seçin;
`2500`, radarın merkezinden 2,5 metre yarıçap demektir. Varsayılan normal
sayaçta `Tümü`, `--demo-game` ile açılan pencerede `1800` mm'dir.
Komutta `--counter-window --game-events --max-distance-mm 2500` kullanılabilir.
Seçim Başlat sırasında uygulanır ve kayıt özetinin `settings.max_distance_mm`
alanında saklanır. Ham ölçümler alan dışındaki hedefler dahil korunur.
Pencere her hedefin uzaklığını ve seçilen alanın dışında kalıp kalmadığını gösterir.
`800-2500` seçimi radara 800 mm'den yakın ve 2500 mm'den uzak hedefleri eler.
Alan içinde birden fazla hedef görülürse sayaç yine adayı iptal eder.
Bu seçenek hareketi dikey zıplama olarak doğrulamaz.


`--game-events` ile açılan pencerede **Sürekli oyun** varsayılan olarak seçilidir.
Başlat sonrasında kalibrasyon tamamlanınca Durdur'a veya pencerenin kapatılmasına
kadar olay gönderimi sürer; `--seconds 120` oyun köprüsünü iki dakikada kesmez.
Süreli deney için Başlat'tan önce Sürekli oyun seçimini kaldırın.
Özet kaydında sürekli oturumlar `session_mode: continuous`, `test_duration_s: null`
olarak belirtilir. Sürekli demo tek, sabit hedefi Başlat'tan sonra bekler;
diğer oturumlarda ilk kalibrasyon 20 saniyede tamamlanamazsa oturum durur.


Radarla oyun için Unity ve radar penceresi birlikte açık kalır. Başlatma sırası
[Unity kurulumunda](../unity/README.md#python-girdileri) anlatılır.

### Gösterim için radar demo modu

`python -m radar --counter-window --game-events --demo-game`
ile açıkça seçilir. Normal sayaç varsayılanı değişmez. Pencerede **DEMO** seçimi,
aktif başlıkta demo bilgisi, kayıt ayarlarında `demo_mode: true` görünür.
Demo tek, kalibre edilmiş hedefte art arda iki ölçümde en az 12 cm/sn hız
ve tetik anında en az 15 mm yer değiştirme görünce olay gönderir. Hareketin
sonunu beklemez. Sonraki tetik için en az 0,8 saniye ve kısa durulma gerekir.
Veri kesintisi, hedef kaybı, alan içinde çoklu hedef ve 500 mm konum sıçraması
korumaları sürer. Oyun kaynağı RADAR olarak seçilir; gönderim gerçek radar
hareketinden gelir. Oturmak, yürümek veya başka hareketler de tetikleyebilir;
bu mod doğrulanmış zıplama sayacı olarak sunulmamalıdır.
