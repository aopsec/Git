using adv7YT.Services;
using FluentAssertions;
using Xunit;

namespace adv7YT.Tests.Services;

public class ProgressParserTests
{
    [Theory]
    [InlineData("[download]  72.3% of   45.67MiB at    2.34MiB/s ETA 00:08", 72.3, "2.34MiB/s", "00:08")]
    [InlineData("[download]   5.0% of  100.00MiB at  500.00KiB/s ETA 03:20",  5.0, "500.00KiB/s", "03:20")]
    [InlineData("[download]   0.5% of    1.23MiB at    1.00MiB/s ETA 00:01",  0.5, "1.00MiB/s", "00:01")]
    public void TryParse_ValidProgressLine_ReturnsTrue(
        string line, double expectedPct, string expectedSpd, string expectedEta)
    {
        var result = ProgressParser.TryParse(line, out var report);

        result.Should().BeTrue();
        report.Should().NotBeNull();
        report!.Percentage.Should().BeApproximately(expectedPct, 0.001);
        report.Speed.Should().Be(expectedSpd);
        report.Eta.Should().Be(expectedEta);
        report.RawLine.Should().Be(line);
    }

    [Theory]
    [InlineData("ERROR: Sign in to confirm your age")]
    [InlineData("[info] Writing video thumbnail to: video.jpg")]
    [InlineData("[download] 100% of 45.67MiB in 00:23 at 1.98MiB/s")]
    [InlineData("")]
    [InlineData("   ")]
    public void TryParse_NonProgressLine_ReturnsFalse(string line)
    {
        var result = ProgressParser.TryParse(line, out var report);

        result.Should().BeFalse();
        report.Should().BeNull();
    }
}
