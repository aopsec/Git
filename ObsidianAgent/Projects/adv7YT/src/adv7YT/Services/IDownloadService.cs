using adv7YT.Models;

namespace adv7YT.Services;

public interface IDownloadService
{
    Task DownloadAsync(
        DownloadRequest request,
        IProgress<ProgressReport>? progress = null,
        IProgress<string>? log = null,
        CancellationToken ct = default);
}
