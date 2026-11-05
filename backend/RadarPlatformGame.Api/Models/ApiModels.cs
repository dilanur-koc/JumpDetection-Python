using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace RadarPlatformGame.Api.Models;

// SQL'den okunan hesap. Sifre ozeti JSON yanitlarina dahil edilmez.
public sealed record UserAccount(int Id, string UserName,
    [property: JsonIgnore] string PasswordHash, DateTime CreatedAtUtc);

// Kullaniciya gonderilebilen profil bilgisidir.
public sealed record UserProfile(int Id, string UserName, DateTime CreatedAtUtc);

public sealed class CredentialsRequest
{
    [Required, StringLength(32, MinimumLength = 3)]
    [RegularExpression(@"^[\p{L}\p{N}_.-]+$",
        ErrorMessage = "Kullanici adi harf, rakam, nokta, tire veya alt cizgi icerebilir.")]
    public string UserName { get; init; } = "";

    [Required, StringLength(128, MinimumLength = 8)]
    public string Password { get; init; } = "";
}

// UserId istekten alinmaz. API onu giris anahtarindan bulur.
public sealed class GameResultRequest
{
    [Range(1, int.MaxValue)]
    public int LevelNumber { get; init; }

    [Range(0, int.MaxValue)]
    public int Score { get; init; }

    [Range(0, int.MaxValue)]
    public int DurationMs { get; init; }

    [Required, RegularExpression("^(keyboard|simulator|radar)$")]
    public string InputSource { get; init; } = "";

    [Required]
    public bool? Completed { get; init; }
}

public sealed record GameResult(long Id, int LevelNumber, int Score, int DurationMs,
    string InputSource, bool Completed, DateTime CreatedAtUtc);

public sealed record LevelProgress(int LevelNumber, bool IsCompleted, DateTime UpdatedAtUtc);
