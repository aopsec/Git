namespace adv7YT.Models;

public enum QualityPreset
{
    Native,
    Fhd,
    Fast
}

public static class QualityPresetExtensions
{
    public static string ToYtDlpFormatFlag(this QualityPreset preset) => preset switch
    {
        QualityPreset.Native => "bestvideo+bestaudio/best",
        QualityPreset.Fhd    => "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        QualityPreset.Fast   => "bestvideo[height<=480]+bestaudio/best[height<=480]",
        _                    => throw new ArgumentOutOfRangeException(nameof(preset), preset, null)
    };
}
