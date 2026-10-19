// JarvisFeed - sends finished five-minute bars from a NinjaTrader 8 chart to Jarvis.
//
// Install: NinjaTrader > New > NinjaScript Editor, right-click Indicators > Import... is not needed:
// copy this file to Documents\NinjaTrader 8\bin\Custom\Indicators\, then press F5 in the
// NinjaScript Editor to compile. Add "JarvisFeed" to an ES or NQ chart set to 5 Minute bars.
//
// What it does: on every finished bar it appends one line to
//   Documents\NinjaTrader 8\jarvis\<instrument>.jarvis.txt
// as   <bar end, UTC epoch seconds>;open;high;low;close;volume
// Jarvis reads that folder. Nothing is sent over the network and nothing is ever traded: it only
// writes a text file. Historical bars on the chart are written once when it loads, so Jarvis
// catches up on anything it missed.
#region Using declarations
using System;
using System.Globalization;
using System.IO;
using System.Text;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class JarvisFeed : Indicator
    {
        private string path;
        private long lastWritten;
        private readonly StringBuilder pending = new StringBuilder();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Writes finished 5-minute bars to a file Jarvis reads. Never trades.";
                Name = "JarvisFeed";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DisplayInDataBox = false;
                PaintPriceMarkers = false;
                IsSuspendedWhileInactive = false;
            }
            else if (State == State.DataLoaded)
            {
                if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 5)
                    Print("JarvisFeed: set this chart to 5 Minute bars - Jarvis forecasts five-minute bars.");
                string folder = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "jarvis");
                Directory.CreateDirectory(folder);
                path = Path.Combine(folder, Instrument.FullName + ".jarvis.txt");
            }
            else if (State == State.Transition)
            {
                Flush(); // the historical backfill, in one write
            }
        }

        protected override void OnBarUpdate()
        {
            if (path == null || BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 5)
                return;
            DateTime end = TimeZoneInfo.ConvertTimeToUtc(Time[0], NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo);
            long t = (long)(end - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
            if (t <= lastWritten)
                return;
            lastWritten = t;
            pending.Append(string.Format(CultureInfo.InvariantCulture, "{0};{1};{2};{3};{4};{5}\n",
                t, Open[0], High[0], Low[0], Close[0], Volume[0]));
            if (State == State.Realtime)
                Flush();
        }

        private void Flush()
        {
            if (pending.Length == 0 || path == null)
                return;
            try
            {
                File.AppendAllText(path, pending.ToString());
                pending.Clear();
            }
            catch (IOException ex)
            {
                Print("JarvisFeed: could not write " + path + ": " + ex.Message);
            }
        }
    }
}
