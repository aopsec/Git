using System.Diagnostics;
using adv7YT.Models;

namespace adv7YT.Services;

public sealed class ConvertService : IConvertService
{
    private readonly IToolExtractor _tools;

    public ConvertService(IToolExtractor tools) => _tools = tools;

    public async Task ConvertAsync(
        ConversionRequest request,
        IProgress<string>? log = null,
        CancellationToken ct = default)
    {
        var ffmpeg = await _tools.GetFfmpegPathAsync(ct);
        var fmt    = request.Format;

        var psi = new ProcessStartInfo
        {
            FileName              = ffmpeg,
            RedirectStandardError = true,
            UseShellExecute       = false,
            CreateNoWindow        = true,
        };

        // Core args
        psi.ArgumentList.Add("-y");
        psi.ArgumentList.Add("-i");
        psi.ArgumentList.Add(request.InputPath);

        // Video codec
        if (fmt.VideoCodec == "none")
        {
            psi.ArgumentList.Add("-vn");
        }
        else
        {
            psi.ArgumentList.Add("-c:v");
            psi.ArgumentList.Add(fmt.VideoCodec);
        }

        // Audio codec
        psi.ArgumentList.Add("-c:a");
        psi.ArgumentList.Add(fmt.AudioCodec);

        // Extra flags — split on space; these are compile-time constants, not user input
        if (!string.IsNullOrEmpty(fmt.ExtraFlags))
        {
            foreach (var flag in fmt.ExtraFlags.Split(' ', StringSplitOptions.RemoveEmptyEntries))
                psi.ArgumentList.Add(flag);
        }

        psi.ArgumentList.Add(request.OutputPath);

        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("Failed to start ffmpeg.");

        var stderrTask = Task.Run(async () =>
        {
            while (true)
            {
                var line = await proc.StandardError.ReadLineAsync(ct);
                if (line is null) break;
                if (!string.IsNullOrWhiteSpace(line))
                    log?.Report(line);
            }
        }, ct);

        try
        {
            await stderrTask;
            await proc.WaitForExitAsync(ct);
        }
        catch (OperationCanceledException)
        {
            // Kill the child process so it doesn't keep running after the user cancels.
            try { proc.Kill(entireProcessTree: true); } catch { /* already exited */ }
            throw;
        }

        if (proc.ExitCode != 0)
            throw new InvalidOperationException($"ffmpeg exited with code {proc.ExitCode}.");
    }
}
