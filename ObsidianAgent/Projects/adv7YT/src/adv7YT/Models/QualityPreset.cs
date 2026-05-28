namespace adv7YT.Models;

public enum QualityPreset
{
    Native,
    Fhd,
    Fast
}

public static class QualityPresetExtensions
{
    // [FEATURE-02] Multi-source friendly format strings. The mp4/m4a-preferred
    // selectors work for YouTube; fallbacks (.../best, .../bestvideo+bestaudio)
    // cover Vimeo, TikTok, Instagram, SoundCloud and the rest of the 1700+
    // sites yt-dlp supports where mp4/m4a streams may not exist.
    public static string ToYtDlpFormatFlag(this QualityPreset preset) => preset switch
    {
        QualityPreset.Native => "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        QualityPreset.Fhd    => "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        QualityPreset.Fast   => "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]",
        _                    => throw new ArgumentOutOfRangeException(nameof(preset), preset, null)
    };
}
