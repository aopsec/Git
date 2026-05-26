namespace adv7YT.Helpers;

/// <summary>
/// SHA-256 hashes of the bundled yt-dlp and ffmpeg binaries.
/// Update these constants whenever the binaries are updated.
/// See CLAUDE.md for the update procedure.
/// </summary>
internal static class ToolHashes
{
    /// <summary>SHA-256 of Assets/yt-dlp.exe</summary>
    public const string YtDlpSha256 = "3db811b366b2da47337d2fcfdfe5bbd9a258dad3f350c54974f005df115a1545";

    /// <summary>SHA-256 of Assets/ffmpeg.exe</summary>
    public const string FfmpegSha256 = "228d7a8556258de907fdb55f36850078ebc7680b84ec30d84ea02e99bec1d1eb";
}
