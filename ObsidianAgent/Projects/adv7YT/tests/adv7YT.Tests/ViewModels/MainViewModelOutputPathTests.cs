using System.IO;
using adv7YT.ViewModels;
using FluentAssertions;
using Xunit;

namespace adv7YT.Tests.ViewModels;

public class MainViewModelOutputPathTests
{
    [Fact]
    public void SameFolderSameExt_AppendsConverted()
    {
        var result = MainViewModel.ResolveOutputPath(@"C:\Videos\test.mp4", @"C:\Videos", "mp4");
        Path.GetFileName(result).Should().Be("test_converted.mp4");
        Path.GetDirectoryName(result).Should().Be(@"C:\Videos");
    }

    [Fact]
    public void SameFolderDifferentExt_NoSuffix()
    {
        var result = MainViewModel.ResolveOutputPath(@"C:\Videos\test.mp4", @"C:\Videos", "mkv");
        Path.GetFileName(result).Should().Be("test.mkv");
    }

    [Fact]
    public void DifferentFolder_SameExt_NoSuffix()
    {
        var result = MainViewModel.ResolveOutputPath(@"C:\Videos\test.mp4", @"D:\Output", "mp4");
        Path.GetFileName(result).Should().Be("test.mp4");
        Path.GetDirectoryName(result).Should().Be(@"D:\Output");
    }

    [Fact]
    public void CaseInsensitiveCollision_AppendsConverted()
    {
        // Input uses uppercase extension; output ext is lowercase — still a collision on Windows.
        var result = MainViewModel.ResolveOutputPath(@"C:\Videos\TEST.MP4", @"C:\Videos", "mp4");
        Path.GetFileName(result).Should().Contain("_converted");
    }
}
