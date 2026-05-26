using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using adv7YT.Models;

namespace adv7YT.Services;

public sealed class RunHistoryService : IRunHistoryService
{
    private readonly string _historyPath;

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented   = true,
        Converters      = { new JsonStringEnumConverter() },
    };

    private readonly SemaphoreSlim _lock = new(1, 1);

    /// <summary>Production constructor — persists to %AppData%\adv7YT\history.json.</summary>
    public RunHistoryService()
        : this(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "adv7YT", "history.json")) { }

    /// <summary>Testability constructor — caller supplies the file path.</summary>
    public RunHistoryService(string historyPath)
        => _historyPath = historyPath;

    public IReadOnlyList<RunRecord> Load()
    {
        if (!File.Exists(_historyPath))
            return Array.Empty<RunRecord>();

        try
        {
            var json    = File.ReadAllText(_historyPath);
            var records = JsonSerializer.Deserialize<List<RunRecord>>(json, JsonOpts);
            return (records ?? new List<RunRecord>())
                .OrderByDescending(r => r.Timestamp)
                .ToList();
        }
        catch
        {
            // Corrupted file — treat as empty; never crash the app.
            return Array.Empty<RunRecord>();
        }
    }

    public async Task AddAsync(RunRecord record, CancellationToken ct = default)
    {
        await _lock.WaitAsync(ct);
        try
        {
            var existing = Load().ToList();   // already sorted newest-first
            existing.Insert(0, record);
            Directory.CreateDirectory(Path.GetDirectoryName(_historyPath)!);
            var json = JsonSerializer.Serialize(existing, JsonOpts);
            await File.WriteAllTextAsync(_historyPath, json, ct);
        }
        finally
        {
            _lock.Release();
        }
    }

    public void Clear()
    {
        if (File.Exists(_historyPath))
            File.Delete(_historyPath);
    }
}
