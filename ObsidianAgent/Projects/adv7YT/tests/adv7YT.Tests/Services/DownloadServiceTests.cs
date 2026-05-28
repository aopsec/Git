using adv7YT.Models;
using adv7YT.Services;
using FluentAssertions;
using Xunit;

namespace adv7YT.Tests.Services;

public class DownloadServiceTests
{
    private const string AnyFormat   = "bestvideo+bestaudio/best";
    private const string AnyTemplate = @"C:\out\%(title)s.%(ext)s";
    private const string AnyFfmpeg   = @"C:\tools\ffmpeg.exe";
    private const string AnyUrl      = "https://youtu.be/dQw4w9WgXcQ";

    // ── MergeFormat routing ───────────────────────────────────────────────

    [Theory]
    [InlineData(DownloadFormatOption.Mp4,  "mp4")]
    [InlineData(DownloadFormatOption.Mkv,  "mkv")]
    [InlineData(DownloadFormatOption.WebM, "webm")]
    public void BuildArgs_MergeFormat_FollowsMergeOutputFormatFlag(
        DownloadFormatOption opt, string expected)
    {
        var args = DownloadService.BuildArgs(AnyFormat, opt.ToMergeFlag(), AnyTemplate, AnyFfmpeg, AnyUrl);
        var idx  = args.ToList().IndexOf("--merge-output-format");

        idx.Should().BeGreaterThan(0, "arg list must contain --merge-output-format");
        args[idx + 1].Should().Be(expected);
    }

    // ── Security invariants ───────────────────────────────────────────────

    [Fact]
    public void BuildArgs_UrlIsLastArg()
    {
        var args = DownloadService.BuildArgs(AnyFormat, "mp4", AnyTemplate, AnyFfmpeg, AnyUrl);
        args[^1].Should().Be(AnyUrl,
            "yt-dlp treats the last positional argument as the URL; placing it last prevents injection via flag-lookalike URLs");
    }

    [Fact]
    public void BuildArgs_ContainsNoPlaylistFlag()
    {
        var args = DownloadService.BuildArgs(AnyFormat, "mp4", AnyTemplate, AnyFfmpeg, AnyUrl);
        args.Should().Contain("--no-playlist");
    }

    [Fact]
    public void BuildArgs_FfmpegLocationFollowsFfmpegLocationFlag()
    {
        var args = DownloadService.BuildArgs(AnyFormat, "mp4", AnyTemplate, AnyFfmpeg, AnyUrl);
        var idx  = args.ToList().IndexOf("--ffmpeg-location");

        idx.Should().BeGreaterThan(0);
        args[idx + 1].Should().Be(AnyFfmpeg);
    }
}
