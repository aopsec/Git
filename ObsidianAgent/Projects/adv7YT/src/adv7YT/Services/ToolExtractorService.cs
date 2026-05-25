using System.Reflection;
using System.Security;
using System.Security.Cryptography;
using adv7YT.Helpers;

namespace adv7YT.Services;

public sealed class ToolExtractorService : IToolExtractor
{
    private static readonly string ToolsDir =
        Path.Combine(Path.GetTempPath(), "adv7YT", "tools");

    // Per-tool semaphores prevent a FileShare.None IOException when two callers
    // (e.g. the background pre-warm in App.OnStartup and the first user-initiated
    // download) race to extract the same binary at the same time.
    private static readonly SemaphoreSlim _ytDlpSem  = new(1, 1);
    private static readonly SemaphoreSlim _ffmpegSem = new(1, 1);

    public Task<string> GetYtDlpPathAsync(CancellationToken ct = default)
        => EnsureToolAsync("adv7YT.Assets.yt-dlp.exe", "yt-dlp.exe", ToolHashes.YtDlpSha256, _ytDlpSem, ct);

    public Task<string> GetFfmpegPathAsync(CancellationToken ct = default)
        => EnsureToolAsync("adv7YT.Assets.ffmpeg.exe", "ffmpeg.exe", ToolHashes.FfmpegSha256, _ffmpegSem, ct);

    private static async Task<string> EnsureToolAsync(
        string resourceName,
        string fileName,
        string expectedSha256,
        SemaphoreSlim semaphore,
        CancellationToken ct)
    {
        var targetPath = Path.Combine(ToolsDir, fileName);

        // Fast path (no lock): already extracted and hash is valid
        if (File.Exists(targetPath) && VerifyHash(targetPath, expectedSha256))
            return targetPath;

        // Serialize concurrent extraction of the same binary (double-checked lock)
        await semaphore.WaitAsync(ct);
        try
        {
            // Re-check inside the lock — a concurrent caller may have extracted while we waited
            if (File.Exists(targetPath) && VerifyHash(targetPath, expectedSha256))
                return targetPath;

            Directory.CreateDirectory(ToolsDir);

            var assembly = Assembly.GetExecutingAssembly();
            await using var stream = assembly.GetManifestResourceStream(resourceName)
                ?? throw new InvalidOperationException(
                    $"Embedded resource '{resourceName}' not found. " +
                    "Ensure yt-dlp.exe and ffmpeg.exe are in Assets/ with EmbeddedResource build action.");

            await using (var file = new FileStream(targetPath, FileMode.Create, FileAccess.Write, FileShare.None))
            {
                await stream.CopyToAsync(file, ct);
            }

            // Post-extraction integrity check
            if (!VerifyHash(targetPath, expectedSha256))
            {
                try { File.Delete(targetPath); } catch { /* best-effort cleanup */ }
                throw new SecurityException(
                    $"SHA-256 mismatch for '{fileName}' after extraction. " +
                    "The bundled binary may be corrupted. Re-build the application.");
            }

            return targetPath;
        }
        finally
        {
            semaphore.Release();
        }
    }

    private static bool VerifyHash(string filePath, string expectedSha256)
    {
        // Skip hash verification for placeholder values (dev mode)
        if (expectedSha256.StartsWith("PLACEHOLDER", StringComparison.OrdinalIgnoreCase))
            return true;

        using var sha = SHA256.Create();
        using var fs = File.OpenRead(filePath);
        var hash = sha.ComputeHash(fs);
        return Convert.ToHexString(hash).Equals(expectedSha256, StringComparison.OrdinalIgnoreCase);
    }
}
