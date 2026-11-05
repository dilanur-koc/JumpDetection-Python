using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Authentication.BearerToken;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Identity;
using Microsoft.Data.SqlClient;
using RadarPlatformGame.Api.Data;
using RadarPlatformGame.Api.Models;

var builder = WebApplication.CreateBuilder(args);

// Controller siniflari HTTP isteklerini karsilar. SQL erisimi GameRepository'dedir.
builder.Services.AddControllers();
builder.Services.AddOpenApi();
builder.Services.AddScoped<GameRepository>();
builder.Services.AddScoped<IPasswordHasher<UserAccount>, PasswordHasher<UserAccount>>();

// ASP.NET Core, giris sonrasi kullanilacak korumali bir erisim anahtari uretir.
// Unity bu anahtari Authorization: Bearer ... basliginda gonderecek.
builder.Services.AddAuthentication(BearerTokenDefaults.AuthenticationScheme)
    .AddBearerToken(options => options.BearerTokenExpiration = TimeSpan.FromHours(1));
builder.Services.AddAuthorization();

// Kayit ve giris isteklerini IP basina dakikada 10 denemeyle sinirlar.
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddPolicy("accounts", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 10,
            Window = TimeSpan.FromMinutes(1),
            QueueLimit = 0
        }));
});

var app = builder.Build();

// SQL baglantisi kesilirse istemciye anlasilir bir hata doner.
// Sifre ve veritabani ayrintilari HTTP yanitina yazilmaz.
app.UseExceptionHandler(handler => handler.Run(async context =>
{
    Exception? error = context.Features.Get<IExceptionHandlerFeature>()?.Error;
    bool databaseError = error is SqlException;
    await Results.Problem(
        statusCode: databaseError ? 503 : 500,
        title: databaseError ? "Veritabanina ulasilamadi." : "Islem tamamlanamadi.")
        .ExecuteAsync(context);
}));

if (app.Environment.IsDevelopment()) app.MapOpenApi();
else app.UseHttpsRedirection();

// Sira onemlidir. Once anahtar dogrulanir, sonra erisim izni denetlenir.
app.UseAuthentication();
app.UseRateLimiter();
app.UseAuthorization();
app.MapControllers();
app.Run();
