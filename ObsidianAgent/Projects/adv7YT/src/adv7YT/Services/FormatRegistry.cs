using adv7YT.Models;

namespace adv7YT.Services;

public static class FormatRegistry
{
    // [FEATURE-01] Expanded from 16 → 30 formats:
    //   Video   x10 (6 original + HEVC MP4, FLV, WMV, 3GP)
    //   Audio   x10 (6 original + WMA, OPUS, AIFF, AC3)
    //   Image   x 4 (NEW — Animated GIF, Animated WebP, PNG Frames, JPEG Frames)
    //   Project x 6 (4 original + ProRes 4444, DNxHR HQ)
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

        // [FEATURE-01] new
        new("ProRes 4444 .mov", "mov", FormatCategory.Project,
            VideoCodec: "prores_ks",
            AudioCodec: "pcm_s16le",
            ExtraFlags: "-profile:v 4 -pix_fmt yuv444p10le",
            Description: "Apple ProRes 4444. Max quality + alpha channel support. For compositing in After Effects."),

        // [FEATURE-01] new
        new("DNxHR HQ .mxf", "mxf", FormatCategory.Project,
            VideoCodec: "dnxhd",
            AudioCodec: "pcm_s16le",
            ExtraFlags: "-profile:v dnxhr_hq -pix_fmt yuv422p",
            Description: "Avid DNxHR HQ. Resolution-independent successor to DNxHD. For Avid Media Composer."),

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

        // [FEATURE-01] new
        new("HEVC MP4", "mp4", FormatCategory.Video,
            VideoCodec: "libx265",
            AudioCodec: "aac",
            ExtraFlags: "-crf 22 -preset slow -pix_fmt yuv420p -tag:v hvc1",
            Description: "H.265 HEVC MP4. ~50% smaller than H.264 at same quality. Requires hardware decoder."),

        // [FEATURE-01] new
        new("FLV", "flv", FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 22 -ar 44100",
            Description: "Flash Video legacy container. Use only for compatibility with older streaming platforms."),

        // [FEATURE-01] new
        new("WMV", "wmv", FormatCategory.Video,
            VideoCodec: "wmv2",
            AudioCodec: "wmav2",
            ExtraFlags: "-b:v 2M -b:a 192k",
            Description: "Windows Media Video. Legacy format for Windows XP/Vista era players."),

        // [FEATURE-01] new
        new("3GP", "3gp", FormatCategory.Video,
            VideoCodec: "libx264",
            AudioCodec: "aac",
            ExtraFlags: "-crf 28 -vf scale=640:-2 -b:a 64k",
            Description: "3GPP Mobile format. Very small files for legacy feature phones and MMS."),

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

        // [FEATURE-01] new
        new("WMA", "wma", FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "wmav2",
            ExtraFlags: "-b:a 192k",
            Description: "Windows Media Audio. Legacy format for Windows Media Player compatibility."),

        // [FEATURE-01] new
        new("OPUS", "opus", FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "libopus",
            ExtraFlags: "-b:a 128k -vbr on -compression_level 10",
            Description: "Opus in .opus container. Best quality/bitrate ratio at low bitrates. VoIP and streaming."),

        // [FEATURE-01] new
        new("AIFF", "aiff", FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "pcm_s16be",
            ExtraFlags: "-ar 44100 -ac 2",
            Description: "AIFF PCM big-endian. Lossless Apple format. Identical quality to WAV; used in macOS/Pro Tools."),

        // [FEATURE-01] new
        new("AC3", "ac3", FormatCategory.Audio,
            VideoCodec: "none",
            AudioCodec: "ac3",
            ExtraFlags: "-b:a 384k",
            Description: "Dolby AC-3 (Dolby Digital) surround. Standard for Blu-ray, DVD, and A/V receivers."),

        // ── Image formats (NEW) ───────────────────────────────────────────────
        // AudioCodec="none" triggers -an in ConvertService ([FIX-BUG-03]).
        new("Animated GIF", "gif", FormatCategory.Image,
            VideoCodec: "gif",
            AudioCodec: "none",
            ExtraFlags: "-vf fps=10,scale=480:-1:flags=lanczos -loop 0",
            Description: "Animated GIF at 10fps, 480px wide. Web-compatible loop. Best for short clips under 15s.",
            IsFrameSequence: false),

        new("Animated WebP", "webp", FormatCategory.Image,
            VideoCodec: "libwebp_anim",
            AudioCodec: "none",
            ExtraFlags: "-vf fps=15,scale=480:-1 -quality 80 -loop 0",
            Description: "Animated WebP at 15fps. ~40% smaller than GIF with 24-bit color and alpha support.",
            IsFrameSequence: false),

        new("PNG Frames", "png", FormatCategory.Image,
            VideoCodec: "png",
            AudioCodec: "none",
            ExtraFlags: "-vf fps=1",
            Description: "PNG frame sequence at 1fps (one image per second). Lossless. Output: frame_0001.png etc.",
            IsFrameSequence: true),

        new("JPEG Frames", "jpg", FormatCategory.Image,
            VideoCodec: "mjpeg",
            AudioCodec: "none",
            ExtraFlags: "-vf fps=1 -q:v 2",
            Description: "JPEG frame sequence at 1fps. High quality VBR. Output: frame_0001.jpg etc.",
            IsFrameSequence: true),
    };

    public static IEnumerable<FormatDefinition> ByCategory(FormatCategory category)
        => All.Where(f => f.Category == category);
}
