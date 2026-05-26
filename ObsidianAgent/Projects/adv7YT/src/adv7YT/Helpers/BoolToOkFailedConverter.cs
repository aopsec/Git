using System.Globalization;
using System.Windows.Data;

namespace adv7YT.Helpers;

/// <summary>Converts bool → "OK" / "FAILED" for the History run-status indicator.</summary>
[ValueConversion(typeof(bool), typeof(string))]
public sealed class BoolToOkFailedConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is true ? "OK" : "FAILED";

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => Binding.DoNothing;
}
