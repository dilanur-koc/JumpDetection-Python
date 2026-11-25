# NEON / LINK proje yönergeleri

Bu depo Python LD2450 radar girdisi, Unity 2D otomatik parkur oyunu ve
ASP.NET Core / SQL Server hesap hizmetini birlikte içerir.

## Kullanıcıyla çalışma

- Türkçe, kısa ve adım adım anlat. Kullanıcının hitap tercihi "balım".
- Oyun arayüzü İngilizce; öğrenmeyi kolaylaştıran kaynak yorumları Türkçe olsun.
- Yalnız istenen proje kapsamında çalış. Masaüstünde başka uygulamalara geçmeden,
  radar/kamera penceresini kontrol etmeden veya ekran kaydı almadan kullanıcıdan
  ilgili kapsam için izin al. Önceki iznin kapsamını genişletme.
- Kullanıcı girişini kendisi yapar; şifre veya token isteme, kaydetme, çıktıya yazma.

## Önce mevcut durumu oku

- `git status --short` ve ilgili dosyaların farklarını incele. Yerel değişiklikleri
  geri alma; mevcut dalı veya main durumunu varsayma.
- `README.md`, `unity/README.md`, `backend/README.md` başlangıç belgeleridir.
- Güncel kamera gösterimi ve dosya haritası: `docs/2026-11-25-demo-guide.md`.
- Güncel radar sorunu ve doğrulanmış testler: `docs/antigravity-start.md`.
  Tarihli notlar geçmiş gözlemdir; çalışma zamanı durumunu ayrıca doğrula.
- Kullanıcı ayrıca istemedikçe commit, push veya main birleşimi yapma.
- Aynı dosyaya birden fazla ajan yazmasın. İnceleme ajanlarının bulgularını ana
  ajan toplasın; uygulama değişikliklerini tek sorumlu yapsın.

## Dosya haritası

- `radar/`: protokol, deneysel hareket adayı sayacı, seri port penceresi ve kayıt.
- `game_bridge/`: localhost UDP olay gönderimi, simülasyon ve tanı alıcısı.
- `jump_detection/`, `main.py`: ayrı kamera karşılaştırma prototipi.
- `unity/RadarPlatformGame/Assets/Scripts/JumpPrototype.cs`: sahne/fizik/UDP/tur.
- `PrototypeCharacter.cs`: kare görseli; `PrototypeInterface.cs`: ekranlar/HUD.
- `GameAccountClient.cs`: Unity ile hesap API'si arasındaki HTTP istemcisi.
  Bu üç dosya da yukarıdaki `Assets/Scripts/` klasöründedir.
- `backend/RadarPlatformGame.Api/`: .NET 10 hesap ve oyun sonuçları API'si.
- `backend/database/01_create_database.sql`: SQL şeması ve kayıt prosedürü.

## Korunacak davranışlar

- `.venv`, `pose_landmarker_lite.task`, yerel kayıtlar ve mevcut hesapları koru.
- Unity kaynağı `unity/RadarPlatformGame` içindedir. `unity/JumpPrototype.cs`
  eski örnektir; onu değiştirerek çalışan oyunun düzeldiğini iddia etme.
- Unity varlıkları taşınırsa `.meta` dosyalarını birlikte taşı; GUID'leri koru.
  `Library`, `Temp`, `Logs`, `.NET bin/obj` kaynak kod değildir.
- API adresi `http://localhost:5269`, sağlık kontrolü `/api/health`;
  veritabanı `RadarPlatformGameDb`. Unity SQL'e doğrudan bağlanmaz.
- Kullanıcı başına en son 5 oyun sonucu tutulur; hesap ve bölüm ilerlemesi
  bu temizlemeye dahil değildir. Şifreler hash olarak saklanır.
- Zıplama olayları HTTP yerine UDP `127.0.0.1:5065` üzerinden gider.
  Tanı alıcısını Unity ile aynı portta birlikte çalıştırma.
- LD2450 düzlemsel X/Y, hız ve hedef yuvaları verir; Y zıplama yüksekliği
  değildir, yuva kalıcı kişi kimliği değildir. Sayım deneysel hareket adayıdır.
- Kullanıcının gerçek zıplaması, radar adayı, gönderilen UDP, kabul edilen olay
  ve oyunda uygulanan zıplama ayrı ölçümlerdir. Eşit olduklarını varsayma.
- Sonucu beklenen sayıya uydurmak için eşik düşürme. Hedef kaybı, kalibrasyon,
  gönderim, paket reddi ve havada olma durumlarını ayrı incele.
- Mor piksel şehir, saydam HUD/zemin, kısa kare izi ve zıplama efektlerini
  kullanıcı istemeden yeniden tasarlama.

## Doğrulama

- Python değişikliğinde mevcut ortamla `python -m unittest discover -s tests -v`.
- API değişikliğinde `dotnet build backend/RadarPlatformGame.Api/RadarPlatformGame.Api.csproj`.
- Unity değişikliğinde gerçek derleme sonucunu ve Console hatalarını kontrol et.
- Donanım testi veya kullanıcı hesabı gerektiren sonucu simülasyonla doğrulanmış
  gibi sunma. Çalıştırılmayan testleri ve kalan belirsizliği açıkça belirt.
- SQL yazma/silme testi için o işleme özel izin ve geçici test hesabı kullan;
  gerçek kullanıcı verisini temizleme. Yerel kayıtları veya sırları yayınlama.
