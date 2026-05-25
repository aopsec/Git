namespace adv7YT.Services;

public interface IToolExtractor
{
    Task<string> GetYtDlpPathAsync(CancellationToken ct = default);
    Task<string> GetFfmpegPathAsync(CancellationToken ct = default);
}
