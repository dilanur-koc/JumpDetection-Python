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
Üç saniyelik geri sayımın ardından tur başlar. 01 oynanabilir; 02–05 henüz geliştirilmedi.

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
& 'C:\Users\Dila\AppData\Local\Programs\Python\Python312\python.exe' -m radar --counter-window --game-events --port COM5 --seconds 20
```

Radar penceresinde Başlat → BAŞLA; ardından Unity'de Start run. COM5 yerel porttur.
Yalnız aktif deney adayları gönderilir; 20 saniye sonunda deney ve gönderim biter.
API hesabı/sonuçları, UDP 5065 zıplama olaylarını taşır. `game_bridge listen` Unity ile aynı portu paylaşamaz.
Kamera oyuna bağlı değildir; radar algılaması hâlâ deneysel hareket adayıdır.

Game ekranındaki Debug, ham UDP/kabul/zıplama sayılarını ve ret nedenini gösterir.
Sayıların eşitliği fiziksel zıplama doğruluğunu göstermez. Havada ikinci zıplama uygulanmaz.

## Öğrenme ve doğrulama

Hız, ilk zıplama hızı ve yerçekimi için Play kapalıyken Prototype → Inspector → Hareket ayarları.
Kod yorumları Türkçedir. En son varsayılan hız 5.2, zıplama 11.5 ve yerçekimi çarpanı 2.5'tir.

[Ayrıntılı çalışma özeti, API uçları ve sınırlar](../docs/2026-11-05-progress.md).
Python testleri ve API derlemesi CI'da çalışır; Unity için otomatik lisanslı CI henüz kurulmadı.