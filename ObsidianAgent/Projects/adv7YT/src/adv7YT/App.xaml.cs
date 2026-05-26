using adv7YT.Services;
using adv7YT.ViewModels;
using adv7YT.Views;
using Microsoft.Extensions.DependencyInjection;
using System.Windows;

namespace adv7YT;

public partial class App : Application
{
    private readonly ServiceProvider _provider;

    public App()
    {
        var services = new ServiceCollection();
        services.AddSingleton<IToolExtractor, ToolExtractorService>();
        services.AddSingleton<IDownloadService, DownloadService>();
        services.AddSingleton<IConvertService, ConvertService>();
        services.AddSingleton<IRunHistoryService, RunHistoryService>();
        services.AddSingleton<MainViewModel>();
        services.AddSingleton<MainWindow>();
        _provider = services.BuildServiceProvider();
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        // Pre-extract both tools in background to avoid first-run delay on download and convert.
        // Exceptions are intentionally swallowed here; they surface when the user actually
        // triggers a download or conversion (DownloadService / ConvertService will re-throw).
        var extractor = _provider.GetRequiredService<IToolExtractor>();
        _ = Task.WhenAll(extractor.GetYtDlpPathAsync(), extractor.GetFfmpegPathAsync());

        var window = _provider.GetRequiredService<MainWindow>();
        window.DataContext = _provider.GetRequiredService<MainViewModel>();
        window.Show();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _provider.Dispose();
        base.OnExit(e);
    }
}
