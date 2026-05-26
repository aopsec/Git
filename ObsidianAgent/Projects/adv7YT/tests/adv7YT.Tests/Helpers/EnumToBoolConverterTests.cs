using System.Globalization;
using System.Windows.Data;
using adv7YT.Helpers;
using adv7YT.Models;
using FluentAssertions;
using Xunit;

namespace adv7YT.Tests.Helpers;

public class EnumToBoolConverterTests
{
    private readonly EnumToBoolConverter _sut = new();
    private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

    // ── Convert ───────────────────────────────────────────────────────────────

    [Theory]
    [InlineData(QualityPreset.Native, "Native", true)]
    [InlineData(QualityPreset.Fhd,    "Fhd",    true)]
    [InlineData(QualityPreset.Fast,   "Fast",   true)]
    [InlineData(QualityPreset.Native, "Fhd",    false)]
    [InlineData(QualityPreset.Fhd,    "Fast",   false)]
    public void Convert_MatchingParameter_ReturnsExpectedBool(
        QualityPreset value, string param, bool expected)
        => _sut.Convert(value, typeof(bool), param, Inv).Should().Be(expected);

    [Fact]
    public void Convert_NonStringParameter_ReturnsFalse()
        => _sut.Convert(QualityPreset.Native, typeof(bool), 42, Inv).Should().Be(false);

    [Fact]
    public void Convert_NullValue_ReturnsFalse()
        => _sut.Convert(null!, typeof(bool), "Native", Inv).Should().Be(false);

    [Fact]
    public void Convert_NullParameter_ReturnsFalse()
        => _sut.Convert(QualityPreset.Native, typeof(bool), null!, Inv).Should().Be(false);

    // ── ConvertBack ───────────────────────────────────────────────────────────

    [Theory]
    [InlineData("Native", QualityPreset.Native)]
    [InlineData("Fhd",    QualityPreset.Fhd)]
    [InlineData("Fast",   QualityPreset.Fast)]
    public void ConvertBack_TrueWithValidParam_ReturnsParsedEnum(string param, QualityPreset expected)
        => _sut.ConvertBack(true, typeof(QualityPreset), param, Inv).Should().Be(expected);

    [Fact]
    public void ConvertBack_False_ReturnsDoNothing()
        => _sut.ConvertBack(false, typeof(QualityPreset), "Native", Inv)
               .Should().Be(Binding.DoNothing);

    [Fact]
    public void ConvertBack_TrueWithNullParam_ReturnsDoNothing()
        => _sut.ConvertBack(true, typeof(QualityPreset), null!, Inv)
               .Should().Be(Binding.DoNothing);
}
