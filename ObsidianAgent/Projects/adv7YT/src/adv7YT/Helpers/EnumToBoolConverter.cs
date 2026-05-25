using System.Globalization;
using System.Windows.Data;

namespace adv7YT.Helpers;

/// <summary>
/// Converts an enum value to bool for RadioButton IsChecked binding.
/// ConverterParameter must be the string name of the enum value to match.
/// </summary>
[ValueConversion(typeof(Enum), typeof(bool))]
public sealed class EnumToBoolConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (parameter is not string paramStr)
            return false;
        return Enum.TryParse(value?.GetType(), paramStr, out var parsed) &&
               Equals(value, parsed);
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is true && parameter is string paramStr)
            return Enum.Parse(targetType, paramStr, ignoreCase: true);
        return Binding.DoNothing;
    }
}
