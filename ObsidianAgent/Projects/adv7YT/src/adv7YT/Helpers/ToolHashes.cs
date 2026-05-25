namespace adv7YT.Helpers;

/// <summary>
/// SHA-256 hashes of the bundled yt-dlp and ffmpeg binaries.
/// Update these constants whenever the binaries are updated.
/// See CLAUDE.md for the update procedure.
/// </summary>
internal static class ToolHashes
{
    /// <summary>SHA-256 of Assets/yt-dlp.exe</summary>
    public const string YtDlpSha256 = "PLACEHOLDER_REPLACE_AFTER_ADDING_BINARY";

    /// <summary>SHA-256 of Assets/ffmpeg.exe</summary>
    public const string FfmpegSha256 = "PLACEHOLDER_REPLACE_AFTER_ADDING_BINARY";
}
