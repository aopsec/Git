using adv7YT.Models;

namespace adv7YT.Services;

public interface IRunHistoryService
{
    /// <summary>Returns all persisted records, newest first.</summary>
    IReadOnlyList<RunRecord> Load();

    /// <summary>Appends a record and persists the updated list.</summary>
    Task AddAsync(RunRecord record, CancellationToken ct = default);

    /// <summary>Deletes the history file.</summary>
    void Clear();
}
