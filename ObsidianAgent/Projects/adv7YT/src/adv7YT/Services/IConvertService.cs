using adv7YT.Models;

namespace adv7YT.Services;

public interface IConvertService
{
    Task ConvertAsync(
        ConversionRequest request,
        IProgress<string>? log = null,
        CancellationToken ct = default);
}
