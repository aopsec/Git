namespace adv7YT.Models;

public sealed record ConversionRequest(
    string InputPath,
    string OutputPath,
    FormatDefinition Format
);
