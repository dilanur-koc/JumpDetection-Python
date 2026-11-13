# Unity — NEON / LINK

Çalışan proje: **RadarPlatformGame/**. Unity Editor **6000.6.7f1** kullanılır.
Kaynaklar `RadarPlatformGame/Assets/Scripts` içindedir; klasör dışındaki eski kopyalama örneği kullanılmaz.

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
- `Assets/Scripts/PrototypeInterface.cs`: statik ana menü, saydam form, bölüm seçimi, geçmiş ve HUD.
- `Assets/Scripts/GameAccountClient.cs`: API istekleri ve bellekte tutulan oturum.
- `Assets/Resources/MenuBackdrop.png`: sabit menü görseli.
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
python -m radar --counter-window --game-events --port COM5 --max-distance-mm 2500 --demo-game
```

Unity'de **RADAR → START RUN** seç. Ayrı radar penceresinde **Başlat**'a bas.
**DEMO AÇIK** ve Unity'de **JUMP TO START** göründüğünde hareket et.
Radar penceresi tur boyunca açık ve aktif kalır. COM5 yerine kendi seri portunu kullan.
Sürekli oyun seçiliyken gönderim **Durdur** ile sonlanır. Demo modunda oturma
ve yürüme gibi hareketler de olayı tetikleyebilir.

Laptop kamerasıyla oynamak için Unity'de **CAMERA** seç ve proje kökünde çalıştır:

```powershell
& '.\.venv\Scripts\python.exe' main.py --game-events --upper-body
```

Baş ve iki omuz kadrajda olmalı. Kamera **READY** gösterdiğinde ve oyun geri
sayımı bittiğinde zıpla. Kamera turunun skoru sonuç ekranında gösterilir.
API hesap ve kayıtlı sonuçları, UDP 5065 zıplama olaylarını taşır.
`game_bridge listen` Unity ile aynı portu paylaşamaz.

Game ekranındaki Debug, ham UDP/kabul/zıplama sayılarını ve ret nedenini gösterir.
Sayıların eşitliği fiziksel zıplama doğruluğunu göstermez. Havada ikinci zıplama uygulanmaz.

## Öğrenme ve doğrulama

Hız, ilk zıplama hızı ve yerçekimi için Play kapalıyken Prototype → Inspector → Hareket ayarları.
Varsayılan ilerleme hızı 2.8, ilk zıplama hızı 11.5 ve yerçekimi çarpanı 2.5'tir.
Engel merkezleri 7 birim aralıklıdır. Varsayılan hızda iki engel arasında 2.5 saniye vardır.

[Ayrıntılı çalışma özeti, API uçları ve sınırlar](../docs/2026-11-05-progress.md).
Python testleri ve API derlemesi CI'da çalışır; Unity için otomatik lisanslı CI henüz kurulmadı.