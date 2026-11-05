# RadarPlatformGame API

Oyunun kullanıcı/sonuç hizmeti `RadarPlatformGame.Api` projesidir (.NET 10).

```powershell
Set-Location 'C:\Users\Dila\Documents\JumpDetectionTest\backend\RadarPlatformGame.Api'
dotnet run --launch-profile http
```

Adres: `http://localhost:5269`. SQL bağlantı kontrolü: `http://localhost:5269/api/health`.
Geliştirme sırasında bu terminal açık kalır; kapatmak API'yi durdurur.

İlk kurulumda SQL Server üzerinde `database/01_create_database.sql` dosyasının tamamını
SSMS'te çalıştırın. Mevcut yerel veritabanı için yeniden oluşturma gerekmez.
`appsettings.json`, Windows kimlik doğrulamasıyla `localhost/RadarPlatformGameDb` kullanır.
Başka sunucu için `ConnectionStrings__GameDatabase` ortam değişkeniyle geçersiz kılınabilir.
Gerçek bağlantı şifrelerini kaynak dosyalarına yazmayın.

Derleme (SQL'in açık olması gerekmez):

```powershell
dotnet build .\RadarPlatformGame.Api\RadarPlatformGame.Api.csproj
```

Uçlar ve veri akışı: [5 Kasım çalışma özeti](../docs/2026-11-05-progress.md).
HTTP örnekleri: [RadarPlatformGame.Api.http](RadarPlatformGame.Api/RadarPlatformGame.Api.http).
Örnek kullanıcı/şifre ve token alanları yer tutucudur; gerçek değerler commit edilmez.
