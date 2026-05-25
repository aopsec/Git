using System.Globalization;
using System.Text.RegularExpressions;
using adv7YT.Models;

namespace adv7YT.Services;

public static class ProgressParser
{
    private static readonly Regex ProgressRegex = new(
        @"\[download\]\s+(?<pct>\d+(?:\.\d+)?)%\s+of\s+[\d.]+\w+\s+at\s+(?<spd>[\d.]+\w+/s)\s+ETA\s+(?<eta>[\d:]+)",
        RegexOptions.Compiled | RegexOptions.ExplicitCapture
    );

    public static bool TryParse(string line, out ProgressReport? report)
    {
        report = null;
        var match = ProgressRegex.Match(line);
        if (!match.Success)
            return false;

        report = new ProgressReport(
            Percentage: double.Parse(match.Groups["pct"].Value, CultureInfo.InvariantCulture),
            Speed:      match.Groups["spd"].Value,
            Eta:        match.Groups["eta"].Value,
            RawLine:    line
        );
        return true;
    }
}
