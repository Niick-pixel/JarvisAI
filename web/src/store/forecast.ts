// Forecast state: what is imported, what the engine needs, and the one job that may be running.
import { create } from "zustand";
import { forecastApi, importExport } from "../api/forecast";
import type { ForecastJob, ForecastStatus, SeriesInfo, VoicePackProgress } from "../api/types";
import { toast } from "./toast";

export type Market = "ES" | "NQ";
export const HORIZONS = [
  { bars: 6, label: "30m" },
  { bars: 12, label: "1h" },
  { bars: 24, label: "2h" },
  { bars: 48, label: "4h" },
] as const;

interface ForecastState {
  symbol: Market;
  horizon: number;
  status: ForecastStatus | null;
  series: SeriesInfo[];
  job: ForecastJob | null;
  pack: VoicePackProgress | null;
  setSymbol: (symbol: Market) => void;
  setHorizon: (horizon: number) => void;
  refresh: () => Promise<void>;
  importFiles: (files: File[]) => Promise<void>;
  run: () => Promise<void>;
  backtest: () => Promise<void>;
  getModel: () => Promise<void>;
  poll: () => Promise<boolean>;
}

const errorText = (error: unknown) => (error instanceof Error ? error.message : String(error));

export const useForecast = create<ForecastState>((set, get) => ({
  symbol: "ES",
  horizon: 12,
  status: null,
  series: [],
  job: null,
  pack: null,
  setSymbol: (symbol) => set({ symbol }),
  setHorizon: (horizon) => set({ horizon }),
  refresh: async () => {
    const [status, series, job, pack] = await Promise.all([
      forecastApi.status(),
      forecastApi.series(),
      forecastApi.job(),
      forecastApi.pack(),
    ]);
    set({ status, series, job, pack });
  },
  importFiles: async (files) => {
    for (const file of files) {
      try {
        const result = await importExport(file, get().symbol);
        const zone = result.zone_assumed ? `assumed ${result.zone}` : `read as ${result.zone}`;
        toast(`${result.symbol} ${result.contract || ""}: ${result.bars.toLocaleString()} bars, times ${zone}.`);
        set({ symbol: (result.symbol === "NQ" || result.symbol === "MNQ" ? "NQ" : "ES") as Market });
      } catch (error) {
        toast(`${file.name}: ${errorText(error)}`, "error");
      }
    }
    set({ series: await forecastApi.series() });
  },
  run: async () => {
    try {
      set({ job: await forecastApi.run(get().symbol, get().horizon) });
    } catch (error) {
      toast(errorText(error), "error");
    }
  },
  backtest: async () => {
    try {
      set({ job: await forecastApi.backtest(get().symbol, get().horizon) });
    } catch (error) {
      toast(errorText(error), "error");
    }
  },
  getModel: async () => {
    set({ pack: await forecastApi.startPack() });
  },
  /** One tick of polling; true while there is still something to wait for. */
  poll: async () => {
    const [job, pack] = await Promise.all([forecastApi.job(), forecastApi.pack()]);
    const packDone = get().pack?.state !== "done" && pack.state === "done";
    set({ job, pack, ...(packDone ? { status: await forecastApi.status() } : {}) });
    return ["loading", "running"].includes(job.state) || ["downloading", "verifying"].includes(pack.state);
  },
}));
