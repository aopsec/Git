using System.Collections.Specialized;
using System.Windows;
using System.Windows.Controls;

namespace adv7YT.Helpers;

/// <summary>
/// Attached property that auto-scrolls a ListBox to the last item
/// whenever its ItemsSource raises CollectionChanged.
/// Usage: helpers:AutoScrollBehavior.IsEnabled="True"
/// </summary>
public static class AutoScrollBehavior
{
    public static readonly DependencyProperty IsEnabledProperty =
        DependencyProperty.RegisterAttached(
            "IsEnabled",
            typeof(bool),
            typeof(AutoScrollBehavior),
            new PropertyMetadata(false, OnIsEnabledChanged));

    public static bool GetIsEnabled(DependencyObject obj)
        => (bool)obj.GetValue(IsEnabledProperty);

    public static void SetIsEnabled(DependencyObject obj, bool value)
        => obj.SetValue(IsEnabledProperty, value);

    private static void OnIsEnabledChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        if (d is not ListBox listBox) return;

        if ((bool)e.NewValue)
            listBox.Loaded += ListBox_Loaded;
        else
            listBox.Loaded -= ListBox_Loaded;
    }

    private static void ListBox_Loaded(object sender, RoutedEventArgs e)
    {
        if (sender is not ListBox listBox) return;

        if (listBox.ItemsSource is INotifyCollectionChanged collection)
            collection.CollectionChanged += (_, args) =>
            {
                if (args.Action == NotifyCollectionChangedAction.Add
                    && listBox.Items.Count > 0)
                {
                    listBox.ScrollIntoView(listBox.Items[^1]);
                }
            };
    }
}
