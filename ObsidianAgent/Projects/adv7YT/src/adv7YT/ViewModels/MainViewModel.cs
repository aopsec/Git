using System.Collections.ObjectModel;
using System.Windows;
using Application = System.Windows.Application; // Disambiguate from System.Windows.Forms.Application
using adv7YT.Models;
using adv7YT.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Wpf.Ui.Appearance;

namespace adv7YT.ViewModels;

public partial class MainViewModel : ObservableObject
{
    private readonly IDownloadService _downloader;
    private readonly IConvertService  _converter;

    public MainViewModel(IDownloadService downloader, IConvertService converter)
    {
        _downloader = downloader;
        _converter  = converter;
        SelectedFormat = FormatRegistry.ByCategory(FormatCategory.Video).First();
        OutputFolder   = Environment.GetFolderPath(Environment.SpecialFolder.MyVideos);
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

    // ── Collections ───────────────────────────────────────────────────────
    public ObservableCollection<string> LogLines { get; } = new();

    public IReadOnlyList<FormatDefinition> VideoFormats
        => FormatRegistry.ByCategory(FormatCategory.Video).ToList();
    public IReadOnlyList<FormatDefinition> AudioFormats
        => FormatRegistry.ByCategory(FormatCategory.Audio).ToList();
    public IReadOnlyList<FormatDefinition> ProjectFormats
        => FormatRegistry.ByCategory(FormatCategory.Project).ToList();

    // ── Commands ──────────────────────────────────────────────────────────
    [RelayCommand(CanExecute = nameof(CanDownload))]
    private async Task DownloadAsync(CancellationToken ct)
    {
        IsRunning     = true;
        ProgressValue = 0;
        LogLines.Clear();

        try
        {
            var request         = new DownloadRequest(Url, SelectedQuality, OutputFolder);
            var progressReporter = new Progress<ProgressReport>(r =>
            {
                ProgressValue = r.Percentage;
                StatusText    = $"{r.Percentage:F1}%  {r.Speed}  ETA {r.Eta}";
            });
            var logReporter = new Progress<string>(line =>
                Application.Current.Dispatcher.Invoke(() => LogLines.Add(line)));

            await _downloader.DownloadAsync(request, progressReporter, logReporter, ct);
            ProgressValue = 100;
            StatusText    = "Download complete.";
        }
        catch (OperationCanceledException)
        {
            StatusText = "Cancelled.";
        }
        catch (Exception ex)
        {
            StatusText = $"Error: {ex.Message}";
        }
        finally
        {
            IsRunning = false;
        }
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

        try
        {
            // Prompt user for input file via OpenFileDialog
            var openDlg = new Microsoft.Win32.OpenFileDialog
            {
                Title  = "Select video to convert",
                Filter = "Video files|*.mp4;*.mkv;*.avi;*.webm;*.mov;*.ts|All files|*.*"
            };
            if (openDlg.ShowDialog() != true)
            {
                StatusText = "Convert cancelled.";
                return;
            }

            var inputPath  = openDlg.FileName;
            var outputPath = Path.Combine(
                OutputFolder,
                Path.GetFileNameWithoutExtension(inputPath) + "." + SelectedFormat.Extension);

            var logReporter = new Progress<string>(line =>
                Application.Current.Dispatcher.Invoke(() => LogLines.Add(line)));

            var req = new ConversionRequest(inputPath, outputPath, SelectedFormat);
            await _converter.ConvertAsync(req, logReporter, ct);
            StatusText = $"Converted: {Path.GetFileName(outputPath)}";
        }
        catch (OperationCanceledException) { StatusText = "Cancelled."; }
        catch (Exception ex)               { StatusText = $"Error: {ex.Message}"; }
        finally                            { IsRunning = false; }
    }

    private bool CanConvert() => !IsRunning && SelectedFormat is not null;

    [RelayCommand]
    private void PasteUrl() => Url = Clipboard.GetText();

    [RelayCommand]
    private void BrowseOutputFolder()
    {
        var dlg = new System.Windows.Forms.FolderBrowserDialog
        {
            Description  = "Select output folder",
            SelectedPath = OutputFolder
        };
        if (dlg.ShowDialog() == System.Windows.Forms.DialogResult.OK)
            OutputFolder = dlg.SelectedPath;
    }

    [RelayCommand]
    private void ToggleTheme()
    {
        IsDarkTheme = !IsDarkTheme;
        ApplicationThemeManager.Apply(
            IsDarkTheme ? ApplicationTheme.Dark : ApplicationTheme.Light);
    }
}
