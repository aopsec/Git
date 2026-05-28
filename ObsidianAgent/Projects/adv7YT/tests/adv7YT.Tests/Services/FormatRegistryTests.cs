using adv7YT.Models;
using adv7YT.Services;
using FluentAssertions;
using Xunit;

namespace adv7YT.Tests.Services;

public class FormatRegistryTests
{
    [Fact]
    public void All_HasThirtyFormats()
        => FormatRegistry.All.Should().HaveCount(30);

    [Theory]
    [InlineData(FormatCategory.Project, 6)]
    [InlineData(FormatCategory.Video,   10)]
    [InlineData(FormatCategory.Audio,   10)]
    [InlineData(FormatCategory.Image,   4)]
    public void ByCategory_ReturnsCorrectCount(FormatCategory category, int expected)
        => FormatRegistry.ByCategory(category).Should().HaveCount(expected);

    [Fact]
    public void AudioFormats_AllHaveVideoCodecNone()
        => FormatRegistry.ByCategory(FormatCategory.Audio)
               .Should().AllSatisfy(f => f.VideoCodec.Should().Be("none"));

    [Fact]
    public void AudioFormats_ExtraFlagsDoNotDuplicateVnFlag()
        // ConvertService adds -vn automatically when VideoCodec == "none".
        // Having -vn in ExtraFlags too would pass the flag twice.
        => FormatRegistry.ByCategory(FormatCategory.Audio)
               .Should().AllSatisfy(f =>
                   (f.ExtraFlags ?? string.Empty)
                       .Split(' ', StringSplitOptions.RemoveEmptyEntries)
                       .Should().NotContain("-vn",
                       because: "ConvertService already adds -vn when VideoCodec == \"none\""));

    [Fact]
    public void ProjectFormats_ContainsProRes()
        => FormatRegistry.ByCategory(FormatCategory.Project)
               .Should().Contain(f => f.Label == "ProRes .mov" && f.Extension == "mov");

    [Fact]
    public void All_NoNullLabels()
        => FormatRegistry.All.Should().AllSatisfy(f => f.Label.Should().NotBeNullOrWhiteSpace());

    [Fact]
    public void All_NoNullExtensions()
        => FormatRegistry.All.Should().AllSatisfy(f => f.Extension.Should().NotBeNullOrWhiteSpace());

    [Fact]
    public void All_AllHaveNonEmptyDescription()
        => FormatRegistry.All.Should()
               .AllSatisfy(f => f.Description.Should().NotBeNullOrWhiteSpace());

    [Fact]
    public void FrameSequenceFormats_HaveIsFrameSequenceTrue()
        // [FEATURE-01] PNG Frames and JPEG Frames write to a directory of
        // numbered files via the frame_%04d.<ext> template, so MainViewModel
        // must mkdir before invoking ffmpeg.
        => FormatRegistry.All
               .Where(f => f.Label is "PNG Frames" or "JPEG Frames")
               .Should().AllSatisfy(f => f.IsFrameSequence.Should().BeTrue())
               .And.HaveCount(2);
}
