# adv7ProTools 0.0.1v — /plan Patch Prompt

## Project location
`/home/aops/OPia/Git/ObsidianAgent/Projects/adv7YT/`

## Stack (do NOT deviate)
- .NET 8 WPF, `net8.0-windows`, win-x64 only
- WPF-UI 4.0.3 (`Wpf.Ui.*`), CommunityToolkit.Mvvm 8.3.2
- xUnit + FluentAssertions + NSubstitute for tests
- Shell injection: **always `psi.ArgumentList.Add()`**, never string concat
- All Process exit codes must be checked; throw on non-zero

---

## BUG-01 · Progress bar frozen at 0%

### Root cause (confirmed via yt-dlp source — YoutubeDL.py)
yt-dlp routes `[download] X%...` lines through `to_screen()`, which writes to
**stdout** by default. The current code calls `ProgressParser.TryParse` only on
`proc.StandardError` — so the regex never matches active download lines.
Additional compounding factors:
1. Python subprocesses use **block-buffering** when piped (not connected to a TTY),
   so lines may be held in an 8 KB buffer instead of flushing line-by-line.
2. yt-dlp may emit **ANSI color escape codes** (`\x1b[...m`) even when piped,
   which can appear before `[download]` and break a strict regex.

### Required changes

**`Services/DownloadService.cs`**

1. Swap the stream roles — stdout carries progress, stderr carries errors:
   ```csharp
   var stdoutTask = ConsumeStreamAsync(proc.StandardOutput, line =>
   {
       log?.Report(line);
       if (ProgressParser.TryParse(line, out var report) && report is not null)
           progress?.Report(report);
   }, ct);

   var stderrTask = ConsumeStreamAsync(proc.StandardError,
       line => log?.Report(line), ct);
   ```

2. Add `PYTHONUNBUFFERED=1` to the process environment so Python flushes each
   progress line immediately:
   ```csharp
   var psi = new ProcessStartInfo { ... };
   psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
   ```

3. Add `--no-colors` to `BuildArgs` (removes ANSI escape codes that would break
   the regex when piped) and update the universal format selector:
   ```csharp
   internal static IReadOnlyList<string> BuildArgs(
       string format, string mergeFormat, string outputTemplate,
       string ffmpegPath, string url)
       => new[]
       {
           "-f",                    format,
           "--merge-output-format", mergeFormat,
           "--newline",
           "--no-colors",            // ← NEW: strips ANSI codes from piped output
           "--no-playlist",
           "--no-mtime",
           "-o",                    outputTemplate,
           "--ffmpeg-location",     ffmpegPath,
           url,
       };
   ```

4. Update `ProgressParser` regex to tolerate any leading ANSI prefix
   (defensive, even after `--no-colors`):
   ```csharp
   private static readonly Regex ProgressRegex = new(
       @"(?:\x1b\[[0-9;]*m)*\[download\]\s+(?<pct>\d+(?:\.\d+)?)%\s+of\s+~?[\d.]+\w+\s+at\s+(?<spd>[\S]+)\s+ETA\s+(?<eta>[\d:]+)",
       RegexOptions.Compiled | RegexOptions.ExplicitCapture
   );
   ```
   Changes vs current:
   - `(?:\x1b\[[0-9;]*m)*` — optional leading ANSI codes
   - `~?` before file size (yt-dlp sometimes prefixes estimated sizes with `~`)
   - `[\S]+` for speed (handles `Unknown` speed during buffering)

**`tests/adv7YT.Tests/Services/DownloadServiceTests.cs`**
Update `BuildArgs` assertions: add assertion that `"--no-colors"` is in the
returned list and that the new universal selector is tested.

**`tests/adv7YT.Tests/Services/ProgressParserTests.cs`**
Add `[InlineData]` cases for:
- Line with leading ANSI prefix: `"\x1b[0m[download]  50.0% of 10.00MiB at 1.00MiB/s ETA 00:10"`
- Line with tilde size: `"[download]  50.0% of ~10.00MiB at 1.00MiB/s ETA 00:10"`

---

## BUG-02 · Convert ComboBox shows only group category headers (Video / Audio / Project)

### Root cause (confirmed — dotnet/wpf issue #10629)
The WPF-UI Fluent theme's `ComboBox` control template uses a `<StackPanel
IsItemsHost="True"/>` inside its popup. WPF requires `<ItemsPresenter/>` for
`GroupStyle` to work — `StackPanel IsItemsHost` silently ignores group descriptors
and renders only the top-level `CollectionViewGroup` objects (one per category),
which is exactly what appears in the screenshot.

### Required fix
Abandon `CollectionViewSource` + `GroupStyle` for this ComboBox. Replace with a
**flat composite list** where non-selectable header rows are interleaved between
format items.

**New file: `Models/FormatItem.cs`**
```csharp
namespace adv7YT.Models;

/// Discriminated union for the flat Convert ComboBox list.
public abstract record FormatItem;
public sealed record FormatHeader(string Name) : FormatItem;
public sealed record FormatEntry(FormatDefinition Format) : FormatItem;
```

**New file: `Helpers/FormatItemTemplateSelector.cs`**
```csharp
using System.Windows;
using System.Windows.Controls;
using adv7YT.Models;

namespace adv7YT.Helpers;

public sealed class FormatItemTemplateSelector : DataTemplateSelector
{
    public DataTemplate? HeaderTemplate  { get; set; }
    public DataTemplate? EntryTemplate   { get; set; }

    public override DataTemplate? SelectTemplate(object item, DependencyObject container)
        => item is FormatHeader ? HeaderTemplate : EntryTemplate;
}
```

**`ViewModels/MainViewModel.cs`** — build flat list for ComboBox:
```csharp
public IReadOnlyList<FormatItem> ConvertFormatList { get; } =
    new[] { FormatCategory.Video, FormatCategory.Audio, FormatCategory.Image, FormatCategory.Project }
        .SelectMany(cat => new FormatItem[]
            { new FormatHeader(cat.ToString()) }
            .Concat(FormatRegistry.ByCategory(cat)
                .Select(f => new FormatEntry(f))))
        .ToList();
```

Remove the `CollectionViewSource` resource from `MainWindow.xaml` and replace the
ComboBox binding with the new flat list. `SelectedConvertFormat` remains
`FormatDefinition?`.

**`Views/MainWindow.xaml`** — Replace the Convert ComboBox block:
```xml
<Window.Resources>
    <!-- Remove or replace FormatsView CollectionViewSource -->
    <local:FormatItemTemplateSelector x:Key="FormatItemSelector">
        <local:FormatItemTemplateSelector.HeaderTemplate>
            <DataTemplate>
                <TextBlock Text="{Binding Name}"
                           FontWeight="SemiBold"
                           Foreground="{DynamicResource TextFillColorSecondaryBrush}"
                           Margin="4,4,0,2"
                           IsHitTestVisible="False"/>
            </DataTemplate>
        </local:FormatItemTemplateSelector.HeaderTemplate>
        <local:FormatItemTemplateSelector.EntryTemplate>
            <DataTemplate>
                <TextBlock Text="{Binding Format.Label}"
                           ToolTip="{Binding Format.Description}"
                           ToolTipService.ShowDuration="8000"
                           Margin="12,0,0,0"/>
            </DataTemplate>
        </local:FormatItemTemplateSelector.EntryTemplate>
    </local:FormatItemTemplateSelector>
</Window.Resources>

<ComboBox ItemsSource="{Binding ConvertFormatList}"
          ItemTemplateSelector="{StaticResource FormatItemSelector}"
          SelectedValuePath="Format"
          SelectedValue="{Binding SelectedConvertFormat}">
    <ComboBox.ItemContainerStyle>
        <Style TargetType="ComboBoxItem"
               BasedOn="{StaticResource {x:Type ComboBoxItem}}">
            <Style.Triggers>
                <!-- Make header rows non-selectable and non-highlighted -->
                <DataTrigger Binding="{Binding}" Value="{x:Null}">
                    <Setter Property="IsEnabled" Value="False"/>
                </DataTrigger>
            </Style.Triggers>
            <Style.DataTriggers>
                <DataTrigger Binding="{Binding}" >
                    <!-- Handled by code-behind or converter if needed -->
                </DataTrigger>
            </Style.DataTriggers>
        </Style>
    </ComboBox.ItemContainerStyle>
</ComboBox>
```

Simpler `ItemContainerStyle` using a converter on `IsEnabled`:
```xml
<ComboBox.ItemContainerStyle>
    <Style TargetType="ComboBoxItem"
           BasedOn="{StaticResource {x:Type ComboBoxItem}}">
        <Setter Property="IsEnabled"
                Value="{Binding Converter={StaticResource IsFormatEntryConverter}}"/>
        <Setter Property="Padding" Value="4,2"/>
    </Style>
</ComboBox.ItemContainerStyle>
```

**New file: `Helpers/IsFormatEntryConverter.cs`**
```csharp
using System.Globalization;
using System.Windows.Data;
using adv7YT.Models;

namespace adv7YT.Helpers;

[ValueConversion(typeof(FormatItem), typeof(bool))]
public sealed class IsFormatEntryConverter : IValueConverter
{
    public object Convert(object v, Type t, object p, CultureInfo c)
        => v is FormatEntry;
    public object ConvertBack(object v, Type t, object p, CultureInfo c)
        => throw new NotSupportedException();
}
```

---

## BUG-03 · ConvertService: add `-an` flag for Image formats (no audio stream)

`ConvertService.cs` currently adds `-vn` when `VideoCodec == "none"` (audio-only).
Image formats (GIF, WebP) have `VideoCodec != "none"` but `AudioCodec == "none"`.
Without `-an`, ffmpeg will try to map an audio stream and error on video-only inputs.

```csharp
// Video codec
if (fmt.VideoCodec == "none")
    psi.ArgumentList.Add("-vn");
else
{
    psi.ArgumentList.Add("-c:v");
    psi.ArgumentList.Add(fmt.VideoCodec);
}

// Audio codec  ← update this section
if (fmt.AudioCodec == "none")
    psi.ArgumentList.Add("-an");          // ← NEW: handles Image category
else
{
    psi.ArgumentList.Add("-c:a");
    psi.ArgumentList.Add(fmt.AudioCodec);
}
```

---

## FEATURE-01 · Expanded format registry (29 formats total)

Update `Models/FormatDefinition.cs` — add `Image` to the enum:
```csharp
public enum FormatCategory { Project, Video, Audio, Image }
```

Update `Services/FormatRegistry.cs` with the full expanded list:

### Video (10 formats — keep 6 existing, add 4)
```csharp
// Keep: MP4, MKV, AVI, WebM, MOV, TS
// ADD:
new("HEVC MP4", "mp4", FormatCategory.Video,
    VideoCodec: "libx265", AudioCodec: "aac",
    ExtraFlags: "-crf 22 -preset slow -pix_fmt yuv420p -tag:v hvc1",
    Description: "H.265 HEVC MP4. ~50% smaller than H.264 at same quality. Requires hardware decoder."),

new("FLV", "flv", FormatCategory.Video,
    VideoCodec: "libx264", AudioCodec: "aac",
    ExtraFlags: "-crf 22 -ar 44100",
    Description: "Flash Video legacy container. Use only for compatibility with older streaming platforms."),

new("WMV", "wmv", FormatCategory.Video,
    VideoCodec: "wmv2", AudioCodec: "wmav2",
    ExtraFlags: "-b:v 2M -b:a 192k",
    Description: "Windows Media Video. Legacy format for Windows XP/Vista era players."),

new("3GP", "3gp", FormatCategory.Video,
    VideoCodec: "libx264", AudioCodec: "aac",
    ExtraFlags: "-crf 28 -vf scale=640:-2 -b:a 64k",
    Description: "3GPP Mobile format. Very small files for legacy feature phones and MMS."),
```

### Audio (10 formats — keep 6 existing, add 4)
```csharp
// Keep: MP3, AAC, WAV, FLAC, OGG, M4A
// ADD:
new("WMA", "wma", FormatCategory.Audio,
    VideoCodec: "none", AudioCodec: "wmav2",
    ExtraFlags: "-b:a 192k",
    Description: "Windows Media Audio. Legacy format for Windows Media Player compatibility."),

new("OPUS", "opus", FormatCategory.Audio,
    VideoCodec: "none", AudioCodec: "libopus",
    ExtraFlags: "-b:a 128k -vbr on -compression_level 10",
    Description: "Opus in .opus container. Best quality/bitrate ratio at low bitrates. VoIP and streaming."),

new("AIFF", "aiff", FormatCategory.Audio,
    VideoCodec: "none", AudioCodec: "pcm_s16be",
    ExtraFlags: "-ar 44100 -ac 2",
    Description: "AIFF PCM big-endian. Lossless Apple format. Identical quality to WAV; used in macOS/Pro Tools."),

new("AC3", "ac3", FormatCategory.Audio,
    VideoCodec: "none", AudioCodec: "ac3",
    ExtraFlags: "-b:a 384k",
    Description: "Dolby AC-3 (Dolby Digital) surround. Standard for Blu-ray, DVD, and A/V receivers."),
```

### Image (4 formats — new category)
```csharp
new("Animated GIF", "gif", FormatCategory.Image,
    VideoCodec: "gif", AudioCodec: "none",
    ExtraFlags: "-vf fps=10,scale=480:-1:flags=lanczos -loop 0",
    Description: "Animated GIF at 10fps, 480px wide. Web-compatible loop. Best for short clips under 15s."),

new("Animated WebP", "webp", FormatCategory.Image,
    VideoCodec: "libwebp_anim", AudioCodec: "none",
    ExtraFlags: "-vf fps=15,scale=480:-1 -quality 80 -loop 0",
    Description: "Animated WebP at 15fps. ~40% smaller than GIF with 24-bit color and alpha support."),

new("PNG Frames", "png", FormatCategory.Image,
    VideoCodec: "png", AudioCodec: "none",
    ExtraFlags: "-vf fps=1",
    Description: "PNG frame sequence at 1fps (one image per second). Lossless. Output: frame_0001.png etc."),

new("JPEG Frames", "jpg", FormatCategory.Image,
    VideoCodec: "mjpeg", AudioCodec: "none",
    ExtraFlags: "-vf fps=1 -q:v 2",
    Description: "JPEG frame sequence at 1fps. High quality VBR. Output: frame_0001.jpg etc."),
```

**Special handling for frame sequences (PNG/JPEG):**
`ConvertService.cs` must detect frame-sequence outputs and set the output template
to `<stem>/frame_%04d.<ext>` rather than `<stem>.<ext>`. Add a property to
`FormatDefinition`:
```csharp
public sealed record FormatDefinition(
    string Label,
    string Extension,
    FormatCategory Category,
    string VideoCodec,
    string AudioCodec,
    string? ExtraFlags,
    string Description,
    bool IsFrameSequence = false);    // ← NEW
```
Set `IsFrameSequence = true` on PNG Frames and JPEG Frames records.

In `MainViewModel.ResolveOutputPath`:
```csharp
internal static string ResolveOutputPath(
    string inputPath, string outputFolder, string extension,
    bool isFrameSequence = false)
{
    if (isFrameSequence)
        return Path.Combine(outputFolder,
            Path.GetFileNameWithoutExtension(inputPath),
            $"frame_%04d.{extension}");

    var candidate = Path.Combine(outputFolder,
        Path.GetFileNameWithoutExtension(inputPath) + "." + extension);
    return string.Equals(candidate, inputPath, StringComparison.OrdinalIgnoreCase)
        ? Path.Combine(outputFolder,
            Path.GetFileNameWithoutExtension(inputPath) + $"_converted.{extension}")
        : candidate;
}
```
Call site in `ConvertAsync`:
```csharp
outputPath = ResolveOutputPath(ConvertInputPath, OutputFolder,
    SelectedConvertFormat.Extension, SelectedConvertFormat.IsFrameSequence);
```
For frame sequences, also create the output directory:
```csharp
if (SelectedConvertFormat.IsFrameSequence)
    Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
```

### Project/NLE (6 formats — keep 4 existing, add 2)
```csharp
// Keep: ProRes .mov (HQ), DNxHD .mxf, H.264 .mov, CineForm .mov
// ADD:
new("ProRes 4444 .mov", "mov", FormatCategory.Project,
    VideoCodec: "prores_ks", AudioCodec: "pcm_s16le",
    ExtraFlags: "-profile:v 4 -pix_fmt yuv444p10le",
    Description: "Apple ProRes 4444. Max quality + alpha channel support. For compositing in After Effects."),

new("DNxHR HQ .mxf", "mxf", FormatCategory.Project,
    VideoCodec: "dnxhd", AudioCodec: "pcm_s16le",
    ExtraFlags: "-profile:v dnxhr_hq -pix_fmt yuv422p",
    Description: "Avid DNxHR HQ. Resolution-independent successor to DNxHD. For Avid Media Composer."),
```

**Total formats after patch: 30** (10 Video, 10 Audio, 4 Image, 6 Project)

---

## FEATURE-02 · Multi-source download (YouTube, Vimeo, TikTok, Instagram, SoundCloud + 1700+)

### Format selector (currently breaks on audio-only sources like SoundCloud)
Update the `QualityPreset` format strings in `Models/QualityPreset.cs`:
```csharp
QualityPreset.Native => "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
QualityPreset.Fhd    => "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
QualityPreset.Fast   => "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]",
```
The trailing `/best` fallback handles audio-only sources (SoundCloud) where no
separate video stream exists.

### UI text
Update the URL TextBox placeholder in `MainWindow.xaml`:
```xml
PlaceholderText="Paste a URL — YouTube, Vimeo, TikTok, Instagram, SoundCloud and 1700+ sites"
```

### No per-site flags required
`Uri.TryCreate` + http/https scheme check in `CanDownload()` is sufficient. yt-dlp's
1700+ extractors handle site-specific routing internally. Do NOT add per-site URL
pattern matching.

---

## FEATURE-03 · Rename to adv7ProTools

**`src/adv7YT/adv7YT.csproj`**
```xml
<AssemblyName>adv7ProTools0.0.1v</AssemblyName>
<Version>0.0.1</Version>
```
Keep `<RootNamespace>adv7YT</RootNamespace>` — internal namespace is not part of the
public exe name. Do NOT rename any `.cs` namespace declarations.

**`Views/MainWindow.xaml`** — update window title:
```xml
Title="adv7ProTools"
```

**`installer/adv7YT.iss`**
```ini
AppName=adv7ProTools
AppVersion=0.0.1
OutputBaseFilename=adv7ProTools0.0.1v-setup
UninstallDisplayIcon={app}\adv7ProTools0.0.1v.exe
[Files]
Source: "..\publish\portable\adv7ProTools0.0.1v.exe"; ...
[Icons]
Name: "{group}\adv7ProTools"; Filename: "{app}\adv7ProTools0.0.1v.exe"
```

---

## Files that MUST be modified

| File | Changes |
|------|---------|
| `Services/DownloadService.cs` | Swap stdout/stderr roles for TryParse; add `PYTHONUNBUFFERED`; add `--no-colors` to BuildArgs; update format selector |
| `Services/ProgressParser.cs` | Tolerate ANSI prefix; tolerate `~` in file size; `[\S]+` for speed |
| `Services/ConvertService.cs` | Add `-an` for `AudioCodec == "none"` when `VideoCodec != "none"` |
| `Services/FormatRegistry.cs` | Expand from 16 → 30 formats across 4 categories |
| `Models/FormatDefinition.cs` | Add `FormatCategory.Image`; add `bool IsFrameSequence = false` property |
| `ViewModels/MainViewModel.cs` | Add `ConvertFormatList`; update `ResolveOutputPath` for frame sequences; update `ConvertAsync` call |
| `Views/MainWindow.xaml` | Replace grouped ComboBox with flat `FormatItem` list; update title; update URL placeholder |
| `Helpers/FormatItemTemplateSelector.cs` | NEW — DataTemplateSelector for header vs entry rows |
| `Helpers/IsFormatEntryConverter.cs` | NEW — `IValueConverter` for `IsEnabled` on header rows |
| `Models/FormatItem.cs` | NEW — `FormatHeader` and `FormatEntry` discriminated union |
| `src/adv7YT/adv7YT.csproj` | Rename `AssemblyName` + `Version` |
| `installer/adv7YT.iss` | Rename `AppName`, `OutputBaseFilename`, icon + file references |

## Files that must NOT be broken

- `Services/RunHistoryService.cs` — zero changes
- `Services/IDownloadService.cs`, `IConvertService.cs`, `IToolExtractor.cs` — zero changes
- `Helpers/AutoScrollBehavior.cs`, `EnumToBoolConverter.cs`, `InvertBoolConverter.cs` — zero changes
- `Models/DownloadRequest.cs`, `DownloadFormatOption.cs`, `QualityPreset.cs` (format strings changed only), `RunRecord.cs` — no structural change
- All existing tests must still pass after the patch

---

## Tests to add / update

### Update `tests/adv7YT.Tests/Services/FormatRegistryTests.cs`
- `All_HasSixteenFormats` → rename to `All_HasThirtyFormats` and assert count == 30
- `ByCategory_ReturnsCorrectCount` InlineData: Video→10, Audio→10, Project→6, Image→4
- Add: `ImageFormats_AllHaveVideoCodecNoneOrImageCodec` — GIF/WebP/PNG/JPEG have correct codecs
- Add: `FrameSequenceFormats_HaveIsFrameSequenceTrue` — PNG and JPEG entries have `IsFrameSequence == true`
- Retain: `AudioFormats_ExtraFlagsDoNotDuplicateVnFlag`, `All_NoNullLabels`, `All_AllHaveNonEmptyDescription`

### Update `tests/adv7YT.Tests/Services/DownloadServiceTests.cs`
- Add `BuildArgs_ContainsNoColorsFlag` — `"--no-colors"` present in result
- Update `BuildArgs_MergeFormat_*` — still passes (no change to merge-format logic)

### Update `tests/adv7YT.Tests/Services/ProgressParserTests.cs`
- Add Theory case: ANSI-prefixed line (e.g. `"\x1b[0m[download]  50.0% of 10.00MiB at 1.00MiB/s ETA 00:10"`) → `TryParse` returns true
- Add Theory case: tilde-size line `"[download]  50.0% of ~10.00MiB at 1.00MiB/s ETA 00:10"` → true

### Update `tests/adv7YT.Tests/ViewModels/MainViewModelOutputPathTests.cs`
- Add `FrameSequence_BuildsDirectoryAndTemplate` — `ResolveOutputPath("C:\\v\\test.mp4", "C:\\out", "png", isFrameSequence: true)` → path contains `frame_%04d.png`

---

## Acceptance criteria (all must be true before PR)

- [ ] Progress bar and status text update live during download (test by downloading any YouTube video)
- [ ] Convert ComboBox opens with all 30 formats visible and selectable; headers (Video/Audio/Image/Project) are greyed out and not selectable
- [ ] Hovering any format in the dropdown shows its Description tooltip for 8 seconds
- [ ] Image category formats (GIF, WebP, PNG Frames, JPEG Frames) appear in the Convert ComboBox
- [ ] Converting a `.mp4` to `PNG Frames` creates a subfolder `<stem>/` with `frame_0001.png`, `frame_0002.png` etc.
- [ ] Downloading a SoundCloud URL with `Native` quality succeeds (does not error on missing video stream)
- [ ] Output `.exe` filename is `adv7ProTools0.0.1v.exe`
- [ ] Window title bar shows "adv7ProTools"
- [ ] `dotnet build` passes with 0 errors, 0 warnings (`TreatWarningsAsErrors=true`)
- [ ] `dotnet test` passes all tests (expect ≥ 68 tests total after updates)

---

## CI / Build note
The GitHub Actions workflow `adv7yt-publish.yml` already handles:
- Asset stub creation for test build
- `dotnet test` on `windows-latest`
- Auto-patching `ToolHashes.cs` with fresh SHA-256 after downloading real binaries
- Publishing `adv7ProTools0.0.1v.exe` and uploading as artifact

Push to `main` with paths touching `ObsidianAgent/Projects/adv7YT/**` to trigger.
