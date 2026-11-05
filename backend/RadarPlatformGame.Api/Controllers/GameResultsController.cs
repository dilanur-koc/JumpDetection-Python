using System.Globalization;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;
using RadarPlatformGame.Api.Data;
using RadarPlatformGame.Api.Models;

namespace RadarPlatformGame.Api.Controllers;

// Bu siniftaki her istek giris gerektirir. Kullanici yalniz kendi verisine erisir.
[ApiController]
[Authorize]
[Route("api/game-results")]
public sealed class GameResultsController(GameRepository database) : ControllerBase
{
    private int UserId => int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!, CultureInfo.InvariantCulture);

    [HttpGet]
    public Task<List<GameResult>> List(CancellationToken cancellationToken) => database.GetResultsAsync(UserId, cancellationToken);

    [HttpPost]
    public async Task<IActionResult> Save(GameResultRequest request, CancellationToken cancellationToken)
    {
        try
        {
            long id = await database.SaveResultAsync(UserId, request, cancellationToken);
            return StatusCode(201, new { id });
        }
        catch (SqlException error) when (error.Number == 50001)
        {
            return Unauthorized();
        }
    }

    [HttpGet("/api/progress")]
    public Task<List<LevelProgress>> Progress(CancellationToken cancellationToken) => database.GetProgressAsync(UserId, cancellationToken);
}
