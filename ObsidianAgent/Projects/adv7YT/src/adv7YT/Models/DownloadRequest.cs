namespace adv7YT.Models;

public sealed record DownloadRequest(
    string Url,
    QualityPreset Quality,
    string OutputDirectory,
    string? OutputTemplate = null
);
