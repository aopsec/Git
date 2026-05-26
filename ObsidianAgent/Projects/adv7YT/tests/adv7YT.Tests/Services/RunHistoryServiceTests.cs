using System.IO;
using adv7YT.Models;
using adv7YT.Services;
using FluentAssertions;

namespace adv7YT.Tests.Services;

/// <summary>
/// Each test gets its own temp file path so tests are fully isolated
/// and never pollute %AppData%\adv7YT\.
/// </summary>
public sealed class RunHistoryServiceTests : IDisposable
{
    private readonly string            _tempDir;
    private readonly string            _histPath;
    private readonly RunHistoryService _sut;

    public RunHistoryServiceTests()
    {
        _tempDir  = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
        Directory.CreateDirectory(_tempDir);
        _histPath = Path.Combine(_tempDir, "history.json");
        _sut      = new RunHistoryService(_histPath);
    }

    public void Dispose() => Directory.Delete(_tempDir, recursive: true);

    // ── AddAsync ──────────────────────────────────────────────────────────

    [Fact]
    public async Task AddAsync_SingleRecord_CreatesFile()
    {
        await _sut.AddAsync(MakeRecord(RunType.Download, success: true));
        File.Exists(_histPath).Should().BeTrue();
    }

    [Fact]
    public async Task AddAsync_SingleRecord_CanBeLoadedBack()
    {
        var record = MakeRecord(RunType.Download, success: true);
        await _sut.AddAsync(record);

        var loaded = _sut.Load();
        loaded.Should().HaveCount(1);
        loaded[0].Id.Should().Be(record.Id);
    }

    // ── Load ordering ─────────────────────────────────────────────────────

    [Fact]
    public async Task Load_MultipleRecords_ReturnsNewestFirst()
    {
        var older = MakeRecord(RunType.Download, success: true,
            timestamp: DateTimeOffset.Now.AddMinutes(-10));
        var newer = MakeRecord(RunType.Convert,  success: true,
            timestamp: DateTimeOffset.Now);

        await _sut.AddAsync(older);
        await _sut.AddAsync(newer);

        var loaded = _sut.Load();
        loaded.Should().HaveCount(2);
        loaded[0].Timestamp.Should().BeAfter(loaded[1].Timestamp);
    }

    // ── Clear ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task Clear_AfterAdd_DeletesFile()
    {
        await _sut.AddAsync(MakeRecord(RunType.Download, success: true));
        _sut.Clear();
        File.Exists(_histPath).Should().BeFalse();
    }

    [Fact]
    public void Clear_WhenFileAbsent_DoesNotThrow()
    {
        var act = () => _sut.Clear();
        act.Should().NotThrow();
    }

    // ── Load edge cases ───────────────────────────────────────────────────

    [Fact]
    public void Load_WhenFileAbsent_ReturnsEmpty()
        => _sut.Load().Should().BeEmpty();

    [Fact]
    public void Load_WhenFileCorrupted_ReturnsEmpty()
    {
        File.WriteAllText(_histPath, "not valid json {{{{");
        _sut.Load().Should().BeEmpty();
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    private static RunRecord MakeRecord(
        RunType runType,
        bool    success,
        DateTimeOffset? timestamp = null) => new()
    {
        RunType      = runType,
        Timestamp    = timestamp ?? DateTimeOffset.Now,
        Source       = "https://example.com/watch?v=test",
        OutputPath   = @"C:\Users\test\Videos\file.mp4",
        FormatLabel  = "MP4",
        Success      = success,
        ErrorMessage = success ? null : "Some error occurred",
    };
}
