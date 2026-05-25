namespace adv7YT.Models;

public sealed record ProgressReport(
    double Percentage,
    string? Speed,
    string? Eta,
    string RawLine
);
