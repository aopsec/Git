namespace adv7YT.Models;

// [FEATURE-01] Image category added for animated/static frame outputs.
public enum FormatCategory { Project, Video, Audio, Image }

public sealed record FormatDefinition(
    string Label,
    string Extension,
    FormatCategory Category,
    string VideoCodec,
    string AudioCodec,
    string? ExtraFlags,
    string Description,
    // [FEATURE-01] When true the output path is a directory + frame_%04d.<ext>
    // template (used by PNG Frames / JPEG Frames). MainViewModel creates the
    // directory before invoking ffmpeg.
    bool IsFrameSequence = false);
