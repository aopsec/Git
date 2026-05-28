using System.Diagnostics;
using System.Globalization;
using System.IO;
using adv7YT.Models;

namespace adv7YT.Services;

public sealed class DownloadService : IDownloadService
{
    private readonly IToolExtractor _tools;

    public DownloadService(IToolExtractor tools) => _tools = tools;

    public async Task DownloadAsync(
        DownloadRequest request,
        IProgress<ProgressReport>? progress = null,
        IProgress<string>? log = null,
        CancellationToken ct = default)
    {
        var ytDlp    = await _tools.GetYtDlpPathAsync(ct);
        var ffmpeg   = await _tools.GetFfmpegPathAsync(ct);
        var format   = request.Quality.ToYtDlpFormatFlag();
        var template = request.OutputTemplate
            ?? Path.Combine(request.OutputDirectory, "%(title)s.%(ext)s");

        var psi = new ProcessStartInfo
        {
            FileName               = ytDlp,
            RedirectStandardOutput = true,
            RedirectStandardError  = true,
            UseShellExecute        = false,
            CreateNoWindow         = true,
        };

        // Use ArgumentList to prevent shell injection from user-supplied URLs
        foreach (var arg in BuildArgs(format, request.MergeFormat, template, ffmpeg, request.Url))
            psi.ArgumentList.Add(arg);

        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("Failed to start yt-dlp.");

        try
        {
            var stderrTask = ConsumeStreamAsync(proc.StandardError, line =>
            {
                log?.Report(line);
                if (ProgressParser.TryParse(line, out var report) && report is not null)
                    progress?.Report(report);
            }, ct);

            var stdoutTask = ConsumeStreamAsync(proc.StandardOutput,
                line => log?.Report(line), ct);

            await Task.WhenAll(stderrTask, stdoutTask);
            await proc.WaitForExitAsync(ct);
        }
        catch (OperationCanceledException)
        {
            // Kill the child process so it doesn't keep running after the user cancels.
            try { proc.Kill(entireProcessTree: true); } catch { /* already exited */ }
            throw;
        }

        if (proc.ExitCode != 0)
            throw new InvalidOperationException($"yt-dlp exited with code {proc.ExitCode}.");
    }

    // Exposed internal for unit tests (InternalsVisibleTo adv7YT.Tests).
    internal static IReadOnlyList<string> BuildArgs(
        string format, string mergeFormat, string outputTemplate, string ffmpegPath, string url)
        => new[]
        {
            "-f",                    format,
            "--merge-output-format", mergeFormat,
            "--newline",
            "--no-playlist",
            "--no-mtime",
            "-o",                    outputTemplate,
            "--ffmpeg-location",     ffmpegPath,
            url,
        };

    private static async Task ConsumeStreamAsync(
        StreamReader reader,
        Action<string> onLine,
        CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(ct);
            if (line is null) break;
            if (!string.IsNullOrWhiteSpace(line))
                onLine(line);
        }
    }
}
