# adv7YT — Engineering Guide

## Stack
- **C# .NET 8** — `net8.0-windows`, WPF, `win-x64`
- **WPF UI 4.0.3** — Fluent Design controls (`FluentWindow`, `TextBox`, etc.)
- **CommunityToolkit.Mvvm 8.3.2** — `[ObservableProperty]`, `[RelayCommand]` source generators
- **xunit + NSubstitute + FluentAssertions** — tests

## Architecture
MVVM. `MainViewModel` owns all state. Services are injected via `Microsoft.Extensions.DependencyInjection` in `App.xaml.cs`.

## Key Security Rules
1. **Never** use `ProcessStartInfo.Arguments` (string). Always use `ProcessStartInfo.ArgumentList` to prevent shell injection from user-supplied URLs.
2. **Never** commit `yt-dlp.exe` or `ffmpeg.exe`. They are `EmbeddedResource` files added manually before build.
3. Validate URLs with `Uri.TryCreate` before passing to yt-dlp.
4. `ToolHashes.cs` constants must be updated whenever binaries are updated.

## Bundled Binaries
Files expected in `src/adv7YT/Assets/` (not in git):
- `yt-dlp.exe` — from https://github.com/yt-dlp/yt-dlp/releases/latest
- `ffmpeg.exe` — from https://www.gyan.dev/ffmpeg/builds/ (`ffmpeg-release-essentials.zip`)

After adding, update `ToolHashes.cs`:
```powershell
Get-FileHash src\adv7YT\Assets\yt-dlp.exe -Algorithm SHA256 | Select Hash
Get-FileHash src\adv7YT\Assets\ffmpeg.exe  -Algorithm SHA256 | Select Hash
```

The `<EmbeddedResource>` block in `adv7YT.csproj` is already active — no edit needed.

## Build Commands
```bash
dotnet build                                                    # compile check
dotnet test                                                     # unit tests
dotnet publish src/adv7YT -c Release -o publish/portable       # portable .exe
iscc installer\adv7YT.iss                                      # Inno Setup installer (runs after publish)
```

## Adding a New Output Format
Edit `src/adv7YT/Services/FormatRegistry.cs` — add a new `FormatDefinition` record to the `All` array. Update `FormatRegistryTests.cs` counts accordingly.

## Commit Prefix
`projects/adv7yt:`
