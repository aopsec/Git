namespace adv7YT.Models;

// [FIX-BUG-02] Discriminated union for the Convert ComboBox.
// Replaces the CollectionViewSource/GroupStyle approach (which broke
// SelectedItem when the user clicked the same group twice in a row) with a
// flat list of header rows + selectable entry rows.
public abstract record FormatItem;
public sealed record FormatHeader(string Name) : FormatItem;
public sealed record FormatEntry(FormatDefinition Format) : FormatItem;
