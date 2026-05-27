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
            ExtraFlags: "-profile:v 3 -pix_fmt yuv422p10le",
            Description: "Apple ProRes 422 HQ. Industry standard for Final Cut Pro / DaVinci Resolve."),

        new("DNxHD .mxf",    "mxf",  FormatCategory.Project,
            VideoCodec: "dnxhd",
            AudioCodec: "pcm_s16le",
            ExtraFlags: "-profile:v dnxhd -b:v 185M -pix_fmt yuv422p",
            Description: "Avid DNxHD 185M. Native format for Avid Media Composer."),

        new("H.264 .mov",    "mov",  FormatCategory.Project,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow -pix_fmt yuv420p -movflags +faststart",
            Description: "H.264 in QuickTime wrapper. Compatible with Adobe Premiere and DaVinci."),

        new("CineForm .mov", "mov",  FormatCategory.Project,
            VideoCodec: "cfhd",
            AudioCodec: "pcm_s16le",
            ExtraFlags: "-quality 5 -pix_fmt yuv422p10le",
            Description: "GoPro CineForm quality 5. Good balance of quality and file size for NLE."),

        // ── Video formats ─────────────────────────────────────────────────────
        new("MP4",  "mp4",  FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow -movflags +faststart",
            Description: "H.264/AAC container. Best compatibility — plays on any device or browser."),

        new("MKV",  "mkv",  FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow",
            Description: "Matroska container. Ideal for archiving; supports multiple audio/subtitle tracks."),

        new("AVI",  "avi",  FormatCategory.Video,
            VideoCodec: "libxvid",
            AudioCodec: "libmp3lame",
            ExtraFlags: "-q:v 3 -q:a 4",
            Description: "Legacy Windows format. Use only if the target software requires AVI."),

        new("WebM", "webm", FormatCategory.Video,
            VideoCodec: "libvpx-vp9",
            AudioCodec: "libopus",
            ExtraFlags: "-crf 31 -b:v 0 -deadline good",
            Description: "VP9/Opus. Open standard optimised for web streaming (YouTube, web players)."),

        new("MOV",  "mov",  FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow -movflags +faststart",
            Description: "QuickTime container. Common on macOS/iOS and Apple ecosystems."),

        new("TS",   "ts",   FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 18 -preset slow",
            Description: "MPEG Transport Stream. Used in broadcast, IPTV, and OBS recordings."),

        // ── Audio formats ─────────────────────────────────────────────────────
        // NOTE: -vn is intentionally absent from all audio ExtraFlags.
        // ConvertService.ConvertAsync adds -vn automatically whenever VideoCodec == "none".
        new("MP3",  "mp3",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "libmp3lame",
            ExtraFlags: "-q:a 0",
            Description: "Universal lossy audio. VBR max quality (-q:a 0). Works everywhere."),

        new("AAC",  "aac",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "aac",
            ExtraFlags: "-b:a 320k",
            Description: "Modern lossy audio at 320 kbps. Better quality than MP3 at same bitrate."),

        new("WAV",  "wav",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "pcm_s16le",
            ExtraFlags: null,
            Description: "Uncompressed PCM. Lossless but very large files; best for audio editing."),

        new("FLAC", "flac", FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "flac",
            ExtraFlags: "-compression_level 8",
            Description: "Lossless compression level 8. Half the size of WAV, bit-perfect quality."),

        new("OGG",  "ogg",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "libvorbis",
            ExtraFlags: "-q:a 6",
            Description: "Vorbis lossy audio. Open format; good quality for music and podcasts."),

        new("M4A",  "m4a",  FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "aac",
            ExtraFlags: "-b:a 256k -movflags +faststart",
            Description: "AAC in MPEG-4 container. Standard format for Apple Music / iTunes."),
    };

    public static IEnumerable<FormatDefinition> ByCategory(FormatCategory category)
        => All.Where(f => f.Category == category);
}
