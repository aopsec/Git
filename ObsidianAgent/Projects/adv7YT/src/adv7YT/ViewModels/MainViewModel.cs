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
        _downloader    = downloader;
        _converter     = converter;
        _history       = history;
        SelectedFormat = FormatRegistry.ByCategory(FormatCategory.Video).First();
        OutputFolder   = Environment.GetFolderPath(Environment.SpecialFolder.MyVideos);

        foreach (var r in _history.Load())
            History.Add(r);
    }

    // ── Observable properties ─────────────────────────────────────────────
    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(DownloadCommand))]
    private string _url = string.Empty;

    [ObservableProperty] private QualityPreset _selectedQuality = QualityPreset.Native;
    [ObservableProperty] private FormatDefinition? _selectedFormat;
    [ObservableProperty] private string _outputFolder = string.Empty;

    [ObservableProperty] private double _progressValue;
    [ObservableProperty] private string _statusText = "Ready";

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(DownloadCommand))]
    [NotifyCanExecuteChangedFor(nameof(ConvertCommand))]
    private bool _isRunning;

    [ObservableProperty] private bool _isLogExpanded;
    [ObservableProperty] private bool _isDarkTheme = true;
    [ObservableProperty] private bool _isHistoryExpanded;

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

    /// <summary>All formats ordered Project → Video → Audio for the grouped ComboBox.</summary>
    public IReadOnlyList<FormatDefinition> AllFormats { get; } =
        FormatRegistry.All.OrderBy(f => f.Category).ToList();

    // ── Commands ──────────────────────────────────────────────────────────
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
            var request          = new DownloadRequest(Url, SelectedQuality, OutputFolder);
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

        // Persist to history regardless of success/failure (CancellationToken.None so
        // the write is not cancelled even if the user triggered cancellation above).
        var record = new RunRecord
        {
            RunType      = RunType.Download,
            Source       = Url,
            OutputPath   = OutputFolder,
            FormatLabel  = string.Empty,   // yt-dlp picks the container; we don't know it here
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

    [RelayCommand(CanExecute = nameof(CanConvert))]
    private async Task ConvertAsync(CancellationToken ct)
    {
        if (SelectedFormat is null) return;

        IsRunning = true;
        LogLines.Clear();

        bool   success      = false;
        string errorMessage = string.Empty;
        string inputPath    = string.Empty;
        string outputPath   = string.Empty;

        try
        {
            var openDlg = new Microsoft.Win32.OpenFileDialog
            {
                Title  = "Select video to convert",
                Filter = "Video files|*.mp4;*.mkv;*.avi;*.webm;*.mov;*.ts|All files|*.*"
            };
            if (openDlg.ShowDialog() != true)
            {
                StatusText = "Convert cancelled.";
                IsRunning  = false;
                return;
            }

            inputPath  = openDlg.FileName;
            outputPath = Path.Combine(
                OutputFolder,
                Path.GetFileNameWithoutExtension(inputPath) + "." + SelectedFormat.Extension);

            var logReporter = new Progress<string>(line =>
                Application.Current.Dispatcher.Invoke(() => LogLines.Add(line)));

            var req = new ConversionRequest(inputPath, outputPath, SelectedFormat);
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

        // Only record if the file dialog was accepted (outputPath non-empty).
        if (!string.IsNullOrEmpty(outputPath))
        {
            var record = new RunRecord
            {
                RunType      = RunType.Convert,
                Source       = inputPath,
                OutputPath   = outputPath,
                FormatLabel  = SelectedFormat?.Label ?? string.Empty,
                Success      = success,
                ErrorMessage = success ? null : errorMessage,
            };
            await _history.AddAsync(record, CancellationToken.None);
            History.Insert(0, record);
        }
    }

    private bool CanConvert() => !IsRunning && SelectedFormat is not null;

    [RelayCommand]
    private void PasteUrl() => Url = Clipboard.GetText();

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

    [RelayCommand]
    private void ToggleTheme()
    {
        IsDarkTheme = !IsDarkTheme;
        ApplicationThemeManager.Apply(
            IsDarkTheme ? ApplicationTheme.Dark : ApplicationTheme.Light);
    }

    /// <summary>Cancels whichever of Download or Convert is currently running.</summary>
    [RelayCommand]
    private void CancelCurrent()
    {
        if (DownloadCancelCommand.CanExecute(null))
            DownloadCancelCommand.Execute(null);
        else if (ConvertCancelCommand.CanExecute(null))
            ConvertCancelCommand.Execute(null);
    }

    [RelayCommand]
    private void ClearHistory()
    {
        _history.Clear();
        History.Clear();
    }
}
