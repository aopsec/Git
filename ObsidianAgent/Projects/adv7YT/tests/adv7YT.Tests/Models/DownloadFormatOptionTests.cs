using adv7YT.Models;
using FluentAssertions;
using Xunit;

namespace adv7YT.Tests.Models;

public class DownloadFormatOptionTests
{
    [Theory]
    [InlineData(DownloadFormatOption.Mp4,  "mp4")]
    [InlineData(DownloadFormatOption.Mkv,  "mkv")]
    [InlineData(DownloadFormatOption.WebM, "webm")]
    public void ToMergeFlag_ReturnsCorrectString(DownloadFormatOption opt, string expected)
        => opt.ToMergeFlag().Should().Be(expected);
}
