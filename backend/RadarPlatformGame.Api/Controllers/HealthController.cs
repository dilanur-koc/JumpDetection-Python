using Microsoft.AspNetCore.Mvc;
using RadarPlatformGame.Api.Data;

namespace RadarPlatformGame.Api.Controllers;

[ApiController]
[Route("api/health")]
public sealed class HealthController(GameRepository database) : ControllerBase
{
    // SELECT DB_NAME yalnizca baglantiyi sinar, veri eklemez.
    [HttpGet]
    public async Task<IActionResult> Get(CancellationToken cancellationToken) =>
        Ok(new { status = "ok", database = await database.CheckDatabaseAsync(cancellationToken) });
}
