using System.Data;
using Microsoft.Data.SqlClient;
using RadarPlatformGame.Api.Models;

namespace RadarPlatformGame.Api.Data;

// Her islem kendi baglantisini acar ve await using ile kapatir.
// SQL degerleri parametrelerle gonderilir, kullanici metni sorguya birlestirilmez.
public sealed class GameRepository(IConfiguration configuration)
{
    private readonly string connectionString = configuration.GetConnectionString("GameDatabase")
        ?? throw new InvalidOperationException("GameDatabase baglantisi tanimli degil.");

    public async Task<string> CheckDatabaseAsync(CancellationToken cancellationToken)
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new SqlCommand("SELECT DB_NAME();", connection);
        return (string)(await command.ExecuteScalarAsync(cancellationToken))!;
    }

    public async Task<UserAccount?> FindByNameAsync(string userName, CancellationToken cancellationToken)
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new SqlCommand(
            "SELECT Id, UserName, PasswordHash, CreatedAtUtc FROM dbo.Users WHERE UserName = @Name;", connection);
        command.Parameters.Add("@Name", SqlDbType.NVarChar, 32).Value = userName;
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        return await reader.ReadAsync(cancellationToken) ? ReadAccount(reader) : null;
    }

    public async Task<UserAccount?> FindByIdAsync(int userId, CancellationToken cancellationToken)
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new SqlCommand(
            "SELECT Id, UserName, PasswordHash, CreatedAtUtc FROM dbo.Users WHERE Id = @Id;", connection);
        command.Parameters.Add("@Id", SqlDbType.Int).Value = userId;
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        return await reader.ReadAsync(cancellationToken) ? ReadAccount(reader) : null;
    }

    public async Task<UserAccount> CreateAccountAsync(string userName, string hash, CancellationToken cancellationToken)
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new SqlCommand("""
            INSERT INTO dbo.Users (UserName, PasswordHash)
            OUTPUT INSERTED.Id, INSERTED.UserName, INSERTED.PasswordHash, INSERTED.CreatedAtUtc
            VALUES (@Name, @Hash);
            """, connection);
        command.Parameters.Add("@Name", SqlDbType.NVarChar, 32).Value = userName;
        command.Parameters.Add("@Hash", SqlDbType.NVarChar, 512).Value = hash;
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        await reader.ReadAsync(cancellationToken);
        return ReadAccount(reader);
    }

    // Hash algoritmasinin ayarlari yenilendiyse basarili giriste ozet de yenilenebilir.
    // Eski ozet kontrolu, eszamanli bir sifre degisikliginin ezilmesini onler.
    public async Task UpdateHashAsync(int userId, string oldHash, string newHash, CancellationToken cancellationToken)
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new SqlCommand("""
            UPDATE dbo.Users SET PasswordHash = @NewHash
            WHERE Id = @Id AND PasswordHash COLLATE Latin1_General_100_BIN2 = @OldHash;
            """, connection);
        command.Parameters.Add("@Id", SqlDbType.Int).Value = userId;
        command.Parameters.Add("@OldHash", SqlDbType.NVarChar, 512).Value = oldHash;
        command.Parameters.Add("@NewHash", SqlDbType.NVarChar, 512).Value = newHash;
        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    public async Task<List<GameResult>> GetResultsAsync(int userId, CancellationToken cancellationToken)
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new SqlCommand("""
            SELECT TOP (5) Id, LevelNumber, Score, DurationMs, InputSource, Completed, CreatedAtUtc
            FROM dbo.GameResults WHERE UserId = @Id ORDER BY CreatedAtUtc DESC, Id DESC;
            """, connection);
        command.Parameters.Add("@Id", SqlDbType.Int).Value = userId;
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        var results = new List<GameResult>();
        while (await reader.ReadAsync(cancellationToken))
        {
            results.Add(new GameResult(reader.GetInt64(0), reader.GetInt32(1), reader.GetInt32(2),
                reader.GetInt32(3), reader.GetString(4), reader.GetBoolean(5), Utc(reader.GetDateTime(6))));
        }
        return results;
    }

    // Hazirladigimiz SQL proseduru ekleme, son 5 kaydi tutma ve ilerlemeyi birlikte yapar.
    // Parametre olan userId, HTTP istek govdesinden degil dogrulanmis anahtardan gelir.
    public async Task<long> SaveResultAsync(int userId, GameResultRequest result, CancellationToken cancellationToken)
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new SqlCommand("dbo.SaveGameResult", connection)
        {
            CommandType = CommandType.StoredProcedure
        };
        command.Parameters.Add("@UserId", SqlDbType.Int).Value = userId;
        command.Parameters.Add("@LevelNumber", SqlDbType.Int).Value = result.LevelNumber;
        command.Parameters.Add("@Score", SqlDbType.Int).Value = result.Score;
        command.Parameters.Add("@DurationMs", SqlDbType.Int).Value = result.DurationMs;
        command.Parameters.Add("@InputSource", SqlDbType.VarChar, 16).Value = result.InputSource;
        command.Parameters.Add("@Completed", SqlDbType.Bit).Value = result.Completed!.Value;
        return (long)(await command.ExecuteScalarAsync(cancellationToken))!;
    }

    public async Task<List<LevelProgress>> GetProgressAsync(int userId, CancellationToken cancellationToken)
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);
        await using var command = new SqlCommand("""
            SELECT LevelNumber, IsCompleted, UpdatedAtUtc
            FROM dbo.UserProgress WHERE UserId = @Id ORDER BY LevelNumber;
            """, connection);
        command.Parameters.Add("@Id", SqlDbType.Int).Value = userId;
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        var progress = new List<LevelProgress>();
        while (await reader.ReadAsync(cancellationToken))
            progress.Add(new LevelProgress(reader.GetInt32(0), reader.GetBoolean(1), Utc(reader.GetDateTime(2))));
        return progress;
    }

    private static DateTime Utc(DateTime date) => DateTime.SpecifyKind(date, DateTimeKind.Utc);

    private static UserAccount ReadAccount(SqlDataReader reader) =>
        new(reader.GetInt32(0), reader.GetString(1), reader.GetString(2), Utc(reader.GetDateTime(3)));
}
