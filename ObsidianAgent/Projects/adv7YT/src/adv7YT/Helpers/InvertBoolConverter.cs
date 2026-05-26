using System.Globalization;
using System.Windows.Data;

namespace adv7YT.Helpers;

/// <summary>
/// Returns the logical negation of a bool binding.
/// Used to drive IsEnabled from an IsRunning flag.
/// </summary>
[ValueConversion(typeof(bool), typeof(bool))]
public sealed class InvertBoolConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b ? !b : Binding.DoNothing;

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b ? !b : Binding.DoNothing;
}
