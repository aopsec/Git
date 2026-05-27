namespace adv7YT.Models;

public enum FormatCategory { Project, Video, Audio }

public sealed record FormatDefinition(
    string Label,
    string Extension,
    FormatCategory Category,
    string VideoCodec,
    string AudioCodec,
    string? ExtraFlags,
    string Description);
