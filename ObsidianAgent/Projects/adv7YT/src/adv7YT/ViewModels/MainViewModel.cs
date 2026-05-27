using System.Collections.ObjectModel;
using System.IO;
using System.Windows;
using adv7YT.Models;
using adv7YT.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Wpf.Ui.Appearance;

namespace adv7YT.ViewModels;

public partial class MainViewModel : ObservableObject
{
    private readonly IDownloadService   _downloader;
    private readonly IConvertService    _converter;
    private readonly IRunHistoryService _history;

    public MainViewModel(IDownloadService downloader, IConvertService converter, IRunHistoryService history)
    {
        _downloader          = downloader;
        _converter           = converter;
        _history             = history;
        SelectedConvertFormat = FormatRegistry.ByCategory(FormatCategory.Video).First();
        OutputFolder          = Environment.GetFolderPath(Environment.SpecialFolder.MyVideos);

        foreach (var r in _history.Load())
            History.Add(r);
    }

    // ── Download properties ───────────────────────────────────────────────
    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(DownloadCommand))]
    private string _url = string.Empty;

    [ObservableProperty] private QualityPreset          _selectedQuality       = QualityPreset.Native;
    [ObservableProperty] private DownloadFormatOption   _selectedDownloadFormat = DownloadFormatOption.Mp4;

    // ── Convert properties ────────────────────────────────────────────────
    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(ConvertCommand))]
    private FormatDefinition? _selectedConvertFormat;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(ConvertCommand))]
    private string _convertInputPath = string.Empty;

    // ── Shared properties ─────────────────────────────────────────────────
    [ObservableProperty] private string _outputFolder = string.Empty;
    [ObservableProperty] private double _progressValue;
    [ObservableProperty] private string _statusText = "Ready";

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(DownloadCommand))]
    [NotifyCanExecuteChangedFor(nameof(ConvertCommand))]
    private bool _isRunning;

    [ObservableProperty] private bool _isLogExpanded;
    [ObservableProperty] private bool _isHistoryExpanded;

    // ── Theme (full property — avoids ToggleSwitch double-flip bug) ───────
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

    // ── Collections ───────────────────────────────────────────────────────
    public ObservableCollection<string>    LogLines { get; } = new();
    public ObservableCollection<RunRecord> History  { get; } = new();

    // Per-category lists kept for test compatibility (FormatRegistryTests.ByCategory_…)
    public IReadOnlyList<FormatDefinition> VideoFormats
        => FormatRegistry.ByCategory(FormatCategory.Video).ToList();
    public IReadOnlyList<FormatDefinition> AudioFormats
        => FormatRegistry.ByCategory(FormatCategory.Audio).ToList();
    public IReadOnlyList<FormatDefinition> ProjectFormats
        => FormatRegistry.ByCategory(FormatCategory.Project).ToList();

    /// <summary>All formats ordered Video → Audio → Project for the grouped ComboBox.</summary>
    public IReadOnlyList<FormatDefinition> AllFormats { get; } =
        FormatRegistry.All
            .OrderBy(f => f.Category switch
            {
                FormatCategory.Video   => 0,
                FormatCategory.Audio   => 1,
                FormatCategory.Project => 2,
                _                      => 3
            })
            .ToList();

    // ── Download commands ─────────────────────────────────────────────────
    [RelayCommand(CanExecute = nameof(CanDownload))]
    private async Task DownloadAsync(CancellationToken ct)
    {
        IsRunning     = true;
        ProgressValue = 0;
        LogLines.Clear();

        bool   success      = false;
        string errorMessage = string.Empty;

        try
        {
            var request = new DownloadRequest(
                Url,
                SelectedQuality,
                OutputFolder,
                MergeFormat: SelectedDownloadFormat.ToMergeFlag());

            var progressReporter = new Progress<ProgressReport>(r =>
            {
                ProgressValue = r.Percentage;
                StatusText    = $"{r.Percentage:F1}%  {r.Speed}  ETA {r.Eta}";
            });
            var logReporter = new Progress<string>(line =>
                Application.Current.Dispatcher.Invoke(() => LogLines.Add(line)));

            await _downloader.DownloadAsync(request, progressReporter, logReporter, ct);
            ProgressValue = 100;
            StatusText    = $"Done → {OutputFolder}";
            success       = true;
        }
        catch (OperationCanceledException)
        {
            StatusText   = "Cancelled.";
            errorMessage = "Cancelled by user.";
        }
        catch (Exception ex)
        {
            StatusText   = $"Error: {ex.Message}";
            errorMessage = ex.Message;
        }
        finally
        {
            IsRunning = false;
        }

        var record = new RunRecord
        {
            RunType      = RunType.Download,
            Source       = Url,
            OutputPath   = OutputFolder,
            FormatLabel  = SelectedDownloadFormat.ToMergeFlag().ToUpperInvariant(),
            Success      = success,
            ErrorMessage = success ? null : errorMessage,
        };
        await _history.AddAsync(record, CancellationToken.None);
        History.Insert(0, record);
    }

    private bool CanDownload() =>
        !IsRunning &&
        !string.IsNullOrWhiteSpace(Url) &&
        Uri.TryCreate(Url, UriKind.Absolute, out var uri) &&
        (uri.Scheme == Uri.UriSchemeHttps || uri.Scheme == Uri.UriSchemeHttp);

    [RelayCommand]
    private void PasteUrl() => Url = Clipboard.GetText();

    // ── Convert commands ──────────────────────────────────────────────────
    [RelayCommand(CanExecute = nameof(CanConvert))]
    private async Task ConvertAsync(CancellationToken ct)
    {
        if (SelectedConvertFormat is null || string.IsNullOrEmpty(ConvertInputPath)) return;

        IsRunning = true;
        LogLines.Clear();

        bool   success      = false;
        string errorMessage = string.Empty;
        string outputPath   = string.Empty;

        try
        {
            outputPath = Path.Combine(
                OutputFolder,
                Path.GetFileNameWithoutExtension(ConvertInputPath) + "." + SelectedConvertFormat.Extension);

            var logReporter = new Progress<string>(line =>
                Application.Current.Dispatcher.Invoke(() => LogLines.Add(line)));

            var req = new ConversionRequest(ConvertInputPath, outputPath, SelectedConvertFormat);
            await _converter.ConvertAsync(req, logReporter, ct);
            StatusText = $"Done → {outputPath}";
            success    = true;
        }
        catch (OperationCanceledException)
        {
            StatusText   = "Cancelled.";
            errorMessage = "Cancelled by user.";
        }
        catch (Exception ex)
        {
            StatusText   = $"Error: {ex.Message}";
            errorMessage = ex.Message;
        }
        finally
        {
            IsRunning = false;
        }

        if (!string.IsNullOrEmpty(outputPath))
        {
            var record = new RunRecord
            {
                RunType      = RunType.Convert,
                Source       = ConvertInputPath,
                OutputPath   = outputPath,
                FormatLabel  = SelectedConvertFormat?.Label ?? string.Empty,
                Success      = success,
                ErrorMessage = success ? null : errorMessage,
            };
            await _history.AddAsync(record, CancellationToken.None);
            History.Insert(0, record);
        }
    }

    private bool CanConvert() =>
        !IsRunning &&
        SelectedConvertFormat is not null &&
        !string.IsNullOrEmpty(ConvertInputPath);

    [RelayCommand]
    private void BrowseInputFile()
    {
        var dlg = new Microsoft.Win32.OpenFileDialog
        {
            Title  = "Select file to convert",
            Filter = "Video and audio files|*.mp4;*.mkv;*.avi;*.webm;*.mov;*.ts;" +
                     "*.mp3;*.aac;*.wav;*.flac;*.ogg;*.m4a|All files|*.*"
        };
        if (dlg.ShowDialog() == true)
            ConvertInputPath = dlg.FileName;
    }

    // ── Shared commands ───────────────────────────────────────────────────
    [RelayCommand]
    private void BrowseOutputFolder()
    {
        var dlg = new Microsoft.Win32.OpenFolderDialog
        {
            Title            = "Select output folder",
            InitialDirectory = OutputFolder
        };
        if (dlg.ShowDialog() == true)
            OutputFolder = dlg.FolderName;
    }

    /// <summary>Cancels whichever of Download or Convert is currently running.</summary>
    [RelayCommand]
    private void CancelCurrent()
    {
        if (DownloadCommand.CanBeCanceled)
            DownloadCommand.Cancel();
        else if (ConvertCommand.CanBeCanceled)
            ConvertCommand.Cancel();
    }

    [RelayCommand]
    private void ClearHistory()
    {
        _history.Clear();
        History.Clear();
    }
}
