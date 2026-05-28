using System.Globalization;
using System.Windows.Data;
using adv7YT.Models;

namespace adv7YT.Helpers;

// [FIX-BUG-02] Returns true when the bound item is a FormatEntry, false for
// FormatHeader. Used in the Convert ComboBox to keep header rows un-selectable
// (ComboBoxItem.IsEnabled = false).
[ValueConversion(typeof(FormatItem), typeof(bool))]
public sealed class IsFormatEntryConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is FormatEntry;

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
