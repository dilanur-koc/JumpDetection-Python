# Unity — NEON / LINK

Çalışan proje: **RadarPlatformGame/**. Unity Editor **6000.6.7f1** kullanılır.
Kaynaklar `RadarPlatformGame/Assets/Scripts` içindedir; klasör dışındaki eski kopyalama örneği kullanılmaz.

[25 Kasım sunum rehberi — arka plan, kare hareketi, ivme, kamera ve efekt dosyaları](../docs/2026-11-25-demo-guide.md).

1. SQL Server hizmeti açık olsun. Mevcut `RadarPlatformGameDb` kurulumu korunur.
2. Ayrı PowerShell'de API'yi aç ve pencereyi açık bırak:

```powershell
Set-Location 'C:\Users\Dila\Documents\JumpDetectionTest\backend\RadarPlatformGame.Api'
dotnet run --launch-profile http
```

3. `http://localhost:5269/api/health` ile API/SQL bağlantısını kontrol et.
4. Unity Hub → Add project from disk → `RadarPlatformGame` klasörünü seç.
5. `Assets/Scenes/Prototype.unity` sahnesini aç; gerekirse **Radar → Oyun sahnesini ac veya olustur** kullan.
6. Play → Play → Sign in → Select a run → giriş kaynağı → Start run.

Kare otomatik ilerler. Keyboard: Space zıplama, R bölüm seçimine dönüş.
Üç saniyelik geri sayımın ardından klavye turu başlar. Simülasyon, radar ve kamera
turlarında kare ilk uygulanabilir zıplamayı bekler. 01 oynanabilir. 02–05 geliştirme aşamasındadır.

## Dosyalar

- `Assets/Scripts/JumpPrototype.cs`: sahne, fizik, hız, kamera, UDP ve tur sonucu.
- `Assets/Scripts/PrototypeCharacter.cs`: kare görseli ve görsel dönüş.
- `Assets/Scripts/NeonStage.cs`: neon şehir, platform ışıkları, iz ve zıplama/iniş efektleri.
- `Assets/Scripts/PrototypeInterface.cs`: statik ana menü, saydam form, bölüm seçimi, geçmiş ve HUD.
- `Assets/Scripts/GameAccountClient.cs`: API istekleri ve bellekte tutulan oturum.
- `Assets/Resources/MenuBackdrop.png`: eski menü görseli; panorama bulunamazsa yedek olarak kullanılır.
- `Assets/Resources/NeonCityBackdrop.png`: özgün mor/cyan/pembe piksel şehir panoraması;
  oyun içinde %58 opaklıkla, oranı korunarak çizilir ve kameradan daha yavaş kayar.
  Giriş ekranında aynı panorama ve yazıların arkasında yumuşak mor bir geçiş kullanılır.
  Üretim aracı ve görsel istemi: `docs/art/neon-city-backdrop-prompt.txt` (depo kökünden).
- `Assets/Resources/ScreenSpotlight2D.shader`: yalnız zeminin yerel aydınlatılması.
- `Assets/Editor/PrototypeSceneSetup.cs`: Radar menüsü ve sahne kurulumu.

## Python girdileri

Simulation seçili ve tur başlamışken:

```powershell
Set-Location 'C:\Users\Dila\Documents\JumpDetectionTest'
& '.\.venv\Scripts\python.exe' -m game_bridge simulate --count 5 --interval 1
```

Radar seçili kullanımda PySerial kurulu Python ile:

```powershell
Set-Location 'C:\Users\Dila\Documents\JumpDetectionTest'
python -m radar --counter-window --game-events --port COM5 --demo-game
```

Unity'de **RADAR DEMO → START RUN** seç. Ayrı radar penceresinde **Başlat**'a bas.
Demo varsayılanı 1800 mm'dir; bu alanın içinde tek kişi durmalı.
Unity geri sayımı bittiğinde ve radar penceresinde **DEMO HAZIR** göründüğünde hareket et.
İlk kabul edilen hareketten sonra kare sürekli ilerler. Engelleri geçmek
için kare yerdeyken yeni bir zıplama algılanmalıdır.
Parkur zemin engelinden sonra ilk platforma ve daha yüksek ikinci platforma çıkar.
Ardından iki parçalı alçak üçüncü platformdan zemine inerek bitiş kapısına ulaşır.
Tüm platformlarda yeniden zıplanabilir; üçüncü platformdaki boşluk bir zıplama ile geçilebilir.
Radar penceresi tur boyunca açık ve aktif kalır. COM5 yerine kendi seri portunu kullan.
Sürekli oyun seçiliyken gönderim **Durdur** ile sonlanır. Demo modunda oturma
ve yürüme gibi hareketler de olayı tetikleyebilir.

Laptop kamerasıyla oynamak için Unity'de **CAMERA** seç ve proje kökünde çalıştır:

```powershell
& '.\.venv\Scripts\python.exe' main.py --game-events --upper-body
```

Baş ve iki omuz kadrajda olmalı. Kamera **READY** gösterdiğinde ve oyun geri
sayımı bittiğinde zıpla. Kamera turunun skoru sonuç ekranında gösterilir.
Kameraya yaklaşıp uzaklaşınca yeni konumda yaklaşık bir saniye sabit dur;
omuz genişliği belirgin değiştiğinde referans otomatik yenilenir.
API hesap ve kayıtlı sonuçları, UDP 5065 zıplama olaylarını taşır.
`game_bridge listen` Unity ile aynı portu paylaşamaz.

Game ekranındaki Debug, ham UDP/kabul/zıplama sayılarını ve ret nedenini gösterir.
Sayıların eşitliği fiziksel zıplama doğruluğunu göstermez. Havada ikinci zıplama uygulanmaz.

## Öğrenme ve doğrulama

Hız, ilk zıplama hızı ve yerçekimi için Play kapalıyken Prototype → Inspector → Hareket ayarları.
Varsayılan ilerleme hızı 3.25, ilk zıplama hızı 11.5 ve yerçekimi çarpanı 2.5'tir.
Kamera modunda havadaki yatay hız yüzde 20 artar (varsayılan 3.9 birim/saniye).
İlk platform X=10–18 aralığında zeminden 1.6 birim, ikinci X=20–28 aralığında 2.6 birim yüksektir.
Üçüncü platform X=29–32 ve X=33–36 aralıklarında iki parçadır; zeminden 1.35 birim yüksektir.
Engeller X=3.5, 14.5, 24 ve 41 konumlarında, bitiş X=46 konumundadır.
Zeminin altında kesik işaretler yoktur. Engeller iç çizgisiz, pahlı köşeli ve neon kenarlı bir yüzeye sahiptir.
Zıplamada 12 cyan kıvılcım ve yumuşak parıltılı bir halka; inişte daha hafif pembe bir efekt çıkar.
Zıplama kıvılcımları 0.32–0.46 saniyede küçülüp solar; halka 0.45 saniye sürer.
Bu efektler fizik veya giriş olayları üretmez.

[Ayrıntılı çalışma özeti, API uçları ve sınırlar](../docs/2026-11-05-progress.md).
Python testleri ve API derlemesi CI'da çalışır; Unity için otomatik lisanslı CI henüz kurulmadı.
