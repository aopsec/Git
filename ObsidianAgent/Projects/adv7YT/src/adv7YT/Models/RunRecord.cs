namespace adv7YT.Models;

public enum RunType { Download, Convert }

/// <summary>
/// A single completed (or failed/cancelled) download or convert operation,
/// persisted in %AppData%\adv7YT\history.json.
/// Init-only properties allow System.Text.Json deserialisation without a custom converter.
/// </summary>
public sealed record RunRecord
{
    public Guid           Id           { get; init; } = Guid.NewGuid();
    public DateTimeOffset Timestamp    { get; init; } = DateTimeOffset.Now;
    public RunType        RunType      { get; init; }
    public string         Source       { get; init; } = string.Empty;  // URL or input file path
    public string         OutputPath   { get; init; } = string.Empty;
    public string         FormatLabel  { get; init; } = string.Empty;
    public bool           Success      { get; init; }
    public string?        ErrorMessage { get; init; }
}
