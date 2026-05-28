using System.Windows;
using System.Windows.Controls;
using adv7YT.Models;

namespace adv7YT.Helpers;

// [FIX-BUG-02] Selects the header or entry DataTemplate per row in the
// Convert ComboBox. Headers are non-interactive labels; entries are the
// selectable FormatDefinition rows.
public sealed class FormatItemTemplateSelector : DataTemplateSelector
{
    public DataTemplate? HeaderTemplate { get; set; }
    public DataTemplate? EntryTemplate  { get; set; }

    public override DataTemplate? SelectTemplate(object item, DependencyObject container)
        => item is FormatHeader ? HeaderTemplate : EntryTemplate;
}
