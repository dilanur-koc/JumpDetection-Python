using System.Globalization;
using System.Security.Claims;
using Microsoft.AspNetCore.Authentication.BearerToken;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Data.SqlClient;
using RadarPlatformGame.Api.Data;
using RadarPlatformGame.Api.Models;

namespace RadarPlatformGame.Api.Controllers;

[ApiController]
[Route("api/auth")]
[RequestSizeLimit(4096)]
public sealed class AuthController(GameRepository database, IPasswordHasher<UserAccount> hasher) : ControllerBase
{
    // Bulunamayan kullanicilarda da ozet kontrolu yapilarak benzer is yuku olusturulur.
    private static readonly UserAccount DummyAccount = new(0, "", "", DateTime.UnixEpoch);
    private static readonly string DummyHash = new PasswordHasher<UserAccount>()
        .HashPassword(DummyAccount, Guid.NewGuid().ToString());

    [HttpPost("register")]
    [EnableRateLimiting("accounts")]
    public async Task<ActionResult<UserProfile>> Register(CredentialsRequest request, CancellationToken cancellationToken)
    {
        // PasswordHasher rastgele salt ekleyerek guvenli sifre ozeti uretir.
        string name = request.UserName.Normalize();
        string hash = hasher.HashPassword(DummyAccount, request.Password);
        try
        {
            UserAccount account = await database.CreateAccountAsync(name, hash, cancellationToken);
            return StatusCode(201, Profile(account));
        }
        catch (SqlException error) when (error.Number is 2601 or 2627)
        {
            // SQL'deki UNIQUE kisiti eszamanli ayni adla kayitlari da yakalar.
            return Conflict(new { message = "Bu kullanici adi zaten alinmis." });
        }
    }

    [HttpPost("login")]
    [EnableRateLimiting("accounts")]
    public async Task<IActionResult> Login(CredentialsRequest request, CancellationToken cancellationToken)
    {
        UserAccount? account = await database.FindByNameAsync(request.UserName.Normalize(), cancellationToken);
        PasswordVerificationResult check = hasher.VerifyHashedPassword(
            account ?? DummyAccount, account?.PasswordHash ?? DummyHash, request.Password);

        if (account == null || check == PasswordVerificationResult.Failed)
            return Unauthorized(new { message = "Kullanici adi veya sifre hatali." });

        if (check == PasswordVerificationResult.SuccessRehashNeeded)
            await database.UpdateHashAsync(account.Id, account.PasswordHash,
                hasher.HashPassword(account, request.Password), cancellationToken);

        // Kullanici kimligi sunucuda dogrulanir ve korumali anahtarin icine konur.
        var identity = new ClaimsIdentity(new[]
        {
            new Claim(ClaimTypes.NameIdentifier, account.Id.ToString(CultureInfo.InvariantCulture)),
            new Claim(ClaimTypes.Name, account.UserName)
        }, BearerTokenDefaults.AuthenticationScheme);
        return SignIn(new ClaimsPrincipal(identity), BearerTokenDefaults.AuthenticationScheme);
    }

    [Authorize]
    [HttpGet("me")]
    public async Task<ActionResult<UserProfile>> Me(CancellationToken cancellationToken)
    {
        int id = int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!, CultureInfo.InvariantCulture);
        UserAccount? account = await database.FindByIdAsync(id, cancellationToken);
        if (account == null) return Unauthorized();
        return Profile(account);
    }

    private static UserProfile Profile(UserAccount account) => new(account.Id, account.UserName, account.CreatedAtUtc);
}
