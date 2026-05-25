using adv7YT.Models;

namespace adv7YT.Services;

public static class FormatRegistry
{
    public static IReadOnlyList<FormatDefinition> All { get; } = new FormatDefinition[]
    {
        // ── Project formats ──────────────────────────────────────────────────
        new("ProRes .mov",    "mov",  FormatCategory.Project,
            VideoCodec: "prores_ks",
            AudioCodec: "pcm_s16le",
            ExtraFlags: "-profile:v 3 -pix_fmt yuv422p10le"),

        new("DNxHD .mxf",    "mxf",  FormatCategory.Project,
            VideoCodec: "dnxhd",
            AudioCodec: "pcm_s16le",
            ExtraFlags: "-profile:v dnxhd -b:v 185M -pix_fmt yuv422p"),

        new("H.264 .mov",    "mov",  FormatCategory.Project,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow -pix_fmt yuv420p -movflags +faststart"),

        new("CineForm .mov", "mov",  FormatCategory.Project,
            VideoCodec: "cfhd",
            AudioCodec: "pcm_s16le",
            ExtraFlags: "-quality 5 -pix_fmt yuv422p10le"),

        // ── Video formats ─────────────────────────────────────────────────────
        new("MP4",  "mp4",  FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow -movflags +faststart"),

        new("MKV",  "mkv",  FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow"),

        new("AVI",  "avi",  FormatCategory.Video,
            VideoCodec: "libxvid",
            AudioCodec: "libmp3lame",
            ExtraFlags: "-q:v 3 -q:a 4"),

        new("WebM", "webm", FormatCategory.Video,
            VideoCodec: "libvpx-vp9",
            AudioCodec: "libopus",
            ExtraFlags: "-crf 31 -b:v 0 -deadline good"),

        new("MOV",  "mov",  FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow -movflags +faststart"),

        new("TS",   "ts",   FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow"),

        // ── Audio formats ─────────────────────────────────────────────────────
        // NOTE: -vn is intentionally absent from all audio ExtraFlags.
        // ConvertService.ConvertAsync adds -vn automatically whenever VideoCodec == "none".
        // Including -vn here would pass the flag twice, which is redundant.
        new("MP3",  "mp3",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "libmp3lame",
            ExtraFlags: "-q:a 0"),

        new("AAC",  "aac",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "aac",
            ExtraFlags: "-b:a 320k"),

        new("WAV",  "wav",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "pcm_s16le",
            ExtraFlags: null),

        new("FLAC", "flac", FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "flac",
            ExtraFlags: "-compression_level 8"),

        new("OGG",  "ogg",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "libvorbis",
            ExtraFlags: "-q:a 6"),

        new("M4A",  "m4a",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "aac",
            ExtraFlags: "-b:a 256k -movflags +faststart"),
    };

    public static IEnumerable<FormatDefinition> ByCategory(FormatCategory category)
        => All.Where(f => f.Category == category);
}
