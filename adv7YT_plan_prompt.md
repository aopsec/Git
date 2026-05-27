# adv7YT 0.0.1v Patch — /plan Prompt

## Project location
`/home/aops/OPia/Git/ObsidianAgent/Projects/adv7YT/`

## Stack (do NOT deviate)
- .NET 8 WPF, `net8.0-windows`, win-x64 only
- WPF-UI 4.0.3 (`Wpf.Ui.*`), CommunityToolkit.Mvvm 8.3.2 (`[ObservableProperty]`, `[RelayCommand]`)
- xUnit + FluentAssertions + NSubstitute for tests
- Shell injection prevention: **always use `psi.ArgumentList.Add()`**, never `psi.Arguments` string concat
- `set -euo pipefail` equivalent: every Process exit code must be checked; throw on non-zero

---

## Bugs to fix — full spec

### BUG-01 · Wrong script flow — separate Download and Convert

**Root cause:**  
All state lives in one flat `MainViewModel`. The Format `ComboBox` (`SelectedFormat`) is shared by
both flows but `DownloadService` ignores it (`--merge-output-format mkv` is hardcoded).
Quality row and Format row are both always visible regardless of which flow is active.

**Required behavior after patch:**

| Flow | Steps shown to user | Controls visible |
|------|---------------------|------------------|
| Download | 1 · Paste URL → 2 · Select Quality → 3 · Select Output Format → 4 · Download | URL TextBox, Quality RadioGroup, DownloadFormat ComboBox, Download button |
| Convert  | 1 · Select file path → 2 · Select Output Format → 3 · Convert | File-picker path display + Browse button, ConvertFormat ComboBox, Convert button |

The two flows must be presented as **two clearly separated UI sections** — use a
`Wpf.Ui.Controls.NavigationView` with two items ("Download" and "Convert") **OR** a
`TabControl` with two `TabItem`s. Do NOT use a single flat panel any longer.

**Download format:**  
The download flow needs its own format selector (`_selectedDownloadFormat`, type
`DownloadFormatOption` — a new lightweight enum or record). Allowed options: **MP4, MKV, WebM**.
This feeds `--merge-output-format` in `DownloadService`. Remove the hardcoded `"mkv"` arg.

**DownloadRequest model change:**  
Add `string MergeFormat` property. `DownloadService` must use `request.MergeFormat` for
`--merge-output-format`. Default value `"mp4"` when not set.

**Convert format:**  
Keep existing `SelectedFormat` / `FormatDefinition` pipeline but scope it to Convert only.
The Convert ComboBox must show all three categories (Video / Audio / Project) grouped exactly
as today via `CollectionViewSource` + `GroupDescriptions`.

---

### BUG-02 · Convert format list — add descriptions + expand to all categories

**Root cause:**  
`FormatDefinition` record has no `Description` field. The ComboBox tooltip is missing.
The user reported "only MP4 can be selected" — this is likely a UI issue where the grouped
ComboBox was not reachable / not open; the registry already has 16 formats, but the UX must
make all formats obviously accessible with an explanation.

**Required changes:**

1. **Add `Description` to `FormatDefinition`** (Models/FormatDefinition.cs):
   ```csharp
   public record FormatDefinition(
       string Label,
       string Extension,
       FormatCategory Category,
       string VideoCodec,
       string AudioCodec,
       string? ExtraFlags,
       string Description);   // ← new
   ```

2. **Populate descriptions** in `FormatRegistry.cs` for all 16 formats. Descriptions must be
   concise, factual, ≤ 120 chars. Required content per category:

   **Video:**
   | Format | Description |
   |--------|-------------|
   | MP4    | "H.264/AAC container. Best compatibility — plays on any device or browser." |
   | MKV    | "Matroska container. Ideal for archiving; supports multiple audio/subtitle tracks." |
   | AVI    | "Legacy Windows format. Use only if the target software requires AVI." |
   | WebM   | "VP9/Opus. Open standard optimised for web streaming (YouTube, web players)." |
   | MOV    | "QuickTime container. Common on macOS/iOS and Apple ecosystems." |
   | TS     | "MPEG Transport Stream. Used in broadcast, IPTV, and OBS recordings." |

   **Audio:**
   | Format | Description |
   |--------|-------------|
   | MP3    | "Universal lossy audio. VBR max quality (-q:a 0). Works everywhere." |
   | AAC    | "Modern lossy audio at 320 kbps. Better quality than MP3 at same bitrate." |
   | WAV    | "Uncompressed PCM. Lossless but very large files; best for audio editing." |
   | FLAC   | "Lossless compression level 8. Half the size of WAV, bit-perfect quality." |
   | OGG    | "Vorbis lossy audio. Open format; good quality for music and podcasts." |
   | M4A    | "AAC in MPEG-4 container. Standard format for Apple Music / iTunes." |

   **Project (NLE export):**
   | Format | Description |
   |--------|-------------|
   | ProRes .mov  | "Apple ProRes 422 HQ. Industry standard for Final Cut Pro / DaVinci Resolve." |
   | DNxHD .mxf   | "Avid DNxHD 185M. Native format for Avid Media Composer." |
   | H.264 .mov   | "H.264 in QuickTime wrapper. Compatible with Adobe Premiere and DaVinci." |
   | CineForm .mov| "GoPro CineForm quality 5. Good balance of quality and file size for NLE." |

3. **Tooltip binding** in `MainWindow.xaml` Convert ComboBox:  
   Each `ComboBoxItem` (via `ItemContainerStyle` or `ItemTemplate`) must bind
   `ToolTip` to `{Binding Description}`. The tooltip must appear on mouse-hover over
   each item in the **open dropdown** as well as on the selected item display.

   Use an `ItemTemplate` on the ConvertFormat `ComboBox`:
   ```xml
   <ComboBox.ItemTemplate>
       <DataTemplate>
           <TextBlock Text="{Binding Label}"
                      ToolTip="{Binding Description}"
                      ToolTipService.ShowDuration="8000"/>
       </DataTemplate>
   </ComboBox.ItemTemplate>
   ```

---

### BUG-03 · Certify Quality flow

**Audit required (read + verify, then fix if wrong):**

Quality presets currently are:
- `Native` → `"bestvideo+bestaudio/best"`  
- `Fhd`    → `"bestvideo[height<=1080]+bestaudio/best[height<=1080]"`  
- `Fast`   → `"bestvideo[height<=480]+bestaudio/best[height<=480]"`  

These are **correct yt-dlp format selectors**. No change needed to `QualityPreset.cs`.

However, **scoping must be verified**:
- Quality row must only be visible on the **Download** tab/section, not on Convert.
- After BUG-01 UI split, confirm the Quality `RadioButton` group is inside the Download panel only.
- `CanDownload()` guard must still validate `!IsRunning && !string.IsNullOrWhiteSpace(Url) && Uri.TryCreate(...)`.
- `CanConvert()` guard must still validate `!IsRunning && SelectedFormat is not null`.
- No quality property should appear in `ConversionRequest`.

If BUG-01 UI split already places Quality inside Download-only section, no further change.

---

### BUG-04 · Theme toggle — fix double-flip desync bug

**Root cause (exact):**  
`MainWindow.xaml` binds `ToggleSwitch.IsChecked="{Binding IsDarkTheme}"` (two-way) **and**
`Command="{Binding ToggleThemeCommand}"`. When the user clicks the toggle:
1. WPF two-way binding sets `IsDarkTheme` to the new value  
2. `ToggleThemeCommand` fires → `ToggleTheme()` executes → `IsDarkTheme = !IsDarkTheme` flips it **back**
3. `ApplicationThemeManager.Apply(...)` applies the wrong (original) theme  

Result: toggle appears to do nothing visually, and state is inverted in memory.

**Fix:**  
Remove `ToggleThemeCommand` / `[RelayCommand]` for theme. Make `IsDarkTheme` a **full property**
(not `[ObservableProperty]`) that applies the theme in its setter:

```csharp
private bool _isDarkTheme = true;
public bool IsDarkTheme
{
    get => _isDarkTheme;
    set
    {
        if (SetProperty(ref _isDarkTheme, value))
            ApplicationThemeManager.Apply(
                value ? ApplicationTheme.Dark : ApplicationTheme.Light);
    }
}
```

Remove the `ToggleTheme()` method and `ToggleThemeCommand` from `MainViewModel.cs`.  
Remove `Command="{Binding ToggleThemeCommand}"` from `MainWindow.xaml` `ToggleSwitch`.  
Keep the two-way `IsChecked` binding — that is now the **only** theme driver.

Verify `App.xaml` keeps `Theme="Dark"` as the startup default (no change needed — `IsDarkTheme = true` in ctor matches).

---

## Files that MUST be modified

| File | Changes |
|------|---------|
| `Models/FormatDefinition.cs` | Add `string Description` parameter to record |
| `Models/DownloadRequest.cs` | Add `string MergeFormat = "mp4"` property |
| `Services/FormatRegistry.cs` | Add descriptions to all 16 `FormatDefinition` constructors |
| `Services/DownloadService.cs` | Replace hardcoded `"mkv"` with `request.MergeFormat` |
| `ViewModels/MainViewModel.cs` | Split state (BUG-01); fix theme property (BUG-04); add `SelectedDownloadFormat` |
| `Views/MainWindow.xaml` | Split into tabs/nav (BUG-01); add format tooltip (BUG-02); fix ToggleSwitch (BUG-04) |

---

## Files that must NOT be broken

- `Services/ConvertService.cs` — zero changes required  
- `Services/ProgressParser.cs` — zero changes required  
- `Services/RunHistoryService.cs` — zero changes required  
- `Helpers/*.cs` — zero changes required (EnumToBoolConverter, InvertBoolConverter, etc.)  
- All existing tests must still pass after the patch  

---

## New model needed: DownloadFormatOption

Create `Models/DownloadFormatOption.cs`:

```csharp
namespace adv7YT.Models;

/// <summary>
/// Container format for yt-dlp --merge-output-format.
/// Only formats that yt-dlp can produce as a merge target are listed.
/// </summary>
public enum DownloadFormatOption
{
    Mp4,   // default
    Mkv,
    WebM,
}

public static class DownloadFormatOptionExtensions
{
    public static string ToMergeFlag(this DownloadFormatOption f) => f switch
    {
        DownloadFormatOption.Mp4  => "mp4",
        DownloadFormatOption.Mkv  => "mkv",
        DownloadFormatOption.WebM => "webm",
        _                         => throw new ArgumentOutOfRangeException(nameof(f), f, null)
    };
}
```

---

## Tests to add / update

1. **`Tests/Models/DownloadFormatOptionTests.cs`** — verify `ToMergeFlag()` returns correct strings for all 3 values.
2. **`Tests/Services/FormatRegistryTests.cs`** — add assertion that every `FormatDefinition` in `FormatRegistry.All` has a non-empty `Description` (prevents future regressions).
3. **`Tests/Services/DownloadServiceTests.cs`** *(new file)* — mock `IToolExtractor`; verify that `DownloadService` passes `request.MergeFormat` value as the argument immediately following `"--merge-output-format"` in `psi.ArgumentList`.

---

## Acceptance criteria (all must be true before PR)

- [ ] Download tab shows: URL field, Quality (Native/FHD/Fast), Format (MP4/MKV/WebM), Download button
- [ ] Convert tab shows: Browse button + selected path label, Format grouped ComboBox (Video/Audio/Project with all 16 formats), Convert button
- [ ] Quality row is NOT visible on the Convert tab
- [ ] Hovering any format in the Convert ComboBox dropdown shows its Description tooltip
- [ ] Downloading with "MP4" selected produces an `.mp4` output file (not `.mkv`)
- [ ] Theme toggle switches between Dark and Light on first click and every subsequent click (no flip-back)
- [ ] App restarts to Dark theme (App.xaml + `IsDarkTheme = true` in ctor)
- [ ] `dotnet build src/adv7YT/adv7YT.csproj -c Release` succeeds with 0 errors, 0 warnings
- [ ] `dotnet test tests/adv7YT.Tests/adv7YT.Tests.csproj` passes all tests
