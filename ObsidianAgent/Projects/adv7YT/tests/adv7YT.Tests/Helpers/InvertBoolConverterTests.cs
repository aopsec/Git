using System.Globalization;
using System.Windows.Data;
using adv7YT.Helpers;
using FluentAssertions;
using Xunit;

namespace adv7YT.Tests.Helpers;

public class InvertBoolConverterTests
{
    private readonly InvertBoolConverter _sut = new();
    private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

    // ── Convert ───────────────────────────────────────────────────────────────

    [Theory]
    [InlineData(true,  false)]
    [InlineData(false, true)]
    public void Convert_Bool_ReturnsInverse(bool input, bool expected)
        => _sut.Convert(input, typeof(bool), null!, Inv).Should().Be(expected);

    [Fact]
    public void Convert_NonBool_ReturnsDoNothing()
        => _sut.Convert("not-a-bool", typeof(bool), null!, Inv)
               .Should().Be(Binding.DoNothing);

    [Fact]
    public void Convert_Null_ReturnsDoNothing()
        => _sut.Convert(null!, typeof(bool), null!, Inv)
               .Should().Be(Binding.DoNothing);

    // ── ConvertBack ───────────────────────────────────────────────────────────

    [Theory]
    [InlineData(true,  false)]
    [InlineData(false, true)]
    public void ConvertBack_Bool_ReturnsInverse(bool input, bool expected)
        => _sut.ConvertBack(input, typeof(bool), null!, Inv).Should().Be(expected);

    [Fact]
    public void ConvertBack_NonBool_ReturnsDoNothing()
        => _sut.ConvertBack("not-a-bool", typeof(bool), null!, Inv)
               .Should().Be(Binding.DoNothing);
}
