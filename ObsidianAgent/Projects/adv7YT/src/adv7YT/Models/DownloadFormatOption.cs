namespace adv7YT.Models;

/// <summary>
/// Container format for yt-dlp --merge-output-format.
/// Only formats yt-dlp can produce as a merge target are listed.
/// </summary>
public enum DownloadFormatOption { Mp4, Mkv, WebM }

public static class DownloadFormatOptionExtensions
{
    public static string ToMergeFlag(this DownloadFormatOption f) => f switch
    {
        DownloadFormatOption.Mp4  => "mp4",
        DownloadFormatOption.Mkv  => "mkv",
        DownloadFormatOption.WebM => "webm",
        _                         => throw new ArgumentOutOfRangeException(nameof(f), f, null)
    };
}
