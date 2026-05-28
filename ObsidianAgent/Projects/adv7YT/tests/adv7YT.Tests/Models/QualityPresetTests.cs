using adv7YT.Models;
using FluentAssertions;
using Xunit;

namespace adv7YT.Tests.Models;

public class QualityPresetTests
{
    [Theory]
    [InlineData(QualityPreset.Native, "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best")]
    [InlineData(QualityPreset.Fhd,   "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]")]
    [InlineData(QualityPreset.Fast,  "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]")]
    public void ToYtDlpFormatFlag_ReturnsExpectedFlag(QualityPreset preset, string expected)
        => preset.ToYtDlpFormatFlag().Should().Be(expected);

    [Fact]
    public void ToYtDlpFormatFlag_InvalidEnum_Throws()
    {
        var act = () => ((QualityPreset)99).ToYtDlpFormatFlag();
        act.Should().Throw<ArgumentOutOfRangeException>();
    }
}
