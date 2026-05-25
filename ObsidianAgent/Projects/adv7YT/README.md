# adv7YT

> Professional Windows desktop app to download YouTube videos and convert them to any format.

## Features

- **Download** YouTube videos via [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Convert** to any format via [ffmpeg](https://ffmpeg.org/)
- Quality presets: Native · FHD 1080p · Fast
- Output formats: MP4, MKV, AVI, WebM, MOV, TS, MP3, AAC, WAV, FLAC, OGG, M4A, ProRes, DNxHD, CineForm
- Zero external dependencies — yt-dlp and ffmpeg are bundled
- Windows 10/11 native Fluent Design UI

## Distribution

- **Portable**: `adv7YT.exe` — no installation required
- **Installer**: `adv7YT-0.1.0-setup.exe` — adds Start Menu and optional desktop shortcut

## Building

### Prerequisites

- .NET 8 SDK (Windows x64)
- Visual Studio 2022 or `dotnet` CLI
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) (for installer only)

### Add bundled binaries

Download and place in `src/adv7YT/Assets/`:

| File | Source |
|------|--------|
| `yt-dlp.exe` | https://github.com/yt-dlp/yt-dlp/releases/latest |
| `ffmpeg.exe` | https://www.gyan.dev/ffmpeg/builds/ → `ffmpeg-release-essentials.zip` → `bin/ffmpeg.exe` |

Then update the SHA-256 hashes in `src/adv7YT/Helpers/ToolHashes.cs`:

```powershell
Get-FileHash src\adv7YT\Assets\yt-dlp.exe  -Algorithm SHA256 | Select Hash
Get-FileHash src\adv7YT\Assets\ffmpeg.exe   -Algorithm SHA256 | Select Hash
```

Uncomment the `EmbeddedResource` block in `adv7YT.csproj`.

### Build & Test

```bash
dotnet build
dotnet test
```

### Publish portable .exe

```bash
dotnet publish src/adv7YT/adv7YT.csproj \
  -c Release -r win-x64 \
  -p:PublishSingleFile=true \
  -p:SelfContained=true \
  -p:IncludeNativeLibrariesForSelfExtract=true \
  -p:EnableCompressionInSingleFile=true \
  -o publish/portable
```

### Build installer

```bash
iscc installer\adv7YT.iss
```
