// Futures forecasting. Kept beside client.ts rather than in it, which is long enough.
import { ApiError, request } from "./client";
import type {
  ErrorBody,
  ForecastJob,
  ForecastStatus,
  ImportResult,
  SeriesInfo,
  VoicePackProgress,
} from "./types";

export const forecastApi = {
  status: () => request<ForecastStatus>("/api/forecast/status"),
  series: () => request<SeriesInfo[]>("/api/forecast/series"),
  clear: (symbol: string) => request<SeriesInfo[]>(`/api/forecast/series/${symbol}`, { method: "DELETE" }),
  job: () => request<ForecastJob>("/api/forecast/job"),
  run: (symbol: string, horizon: number) =>
    request<ForecastJob>("/api/forecast/run", { method: "POST", body: JSON.stringify({ symbol, horizon }) }),
  backtest: (symbol: string, horizon: number, windows = 12) =>
    request<ForecastJob>("/api/forecast/backtest", {
      method: "POST",
      body: JSON.stringify({ symbol, horizon, windows }),
    }),
  pack: () => request<VoicePackProgress>("/api/forecast/pack"),
  startPack: () => request<VoicePackProgress>("/api/forecast/pack", { method: "POST" }),
};

/** The export as the raw body, like voice clips: multipart would be a dependency for one field. */
export async function importExport(file: File, symbol: string): Promise<ImportResult> {
  const query = new URLSearchParams({ filename: file.name, symbol });
  const response = await fetch(`/api/forecast/import?${query}`, { method: "POST", body: file });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorBody | null;
    throw new ApiError(body ?? { code: "internal", message: `${response.status} ${response.statusText}` });
  }
  return (await response.json()) as ImportResult;
}
