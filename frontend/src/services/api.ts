// src/services/api.ts
// Semua request ke "/api/*" → diteruskan proxy Vite ke http://localhost:8000
// JANGAN pakai "http://localhost:8000" langsung → CORS error di browser

const BASE_URL = "/api";

// ── Types ────────────────────────────────────────────────────────

export interface ForecastResponse {
  forecast: number[];
  upper: number[];
  lower: number[];
  order: [number, number, number];
  aic: number | null;
  weeks: string[];
  last_sales: number;
}

export interface EvaluationResponse {
  order: [number, number, number];
  aic: number | null;
  mae: number;
  rmse: number;
  mape: number;
  actual_train: number[];
  actual_test: number[];
  fitted: number[];
  dates_train: string[];
  dates_test: string[];
}

export interface SeasonalityCell {
  month: string;
  week_in_month: string;
  avg_sales: number;
}

export interface EDAResponse {
  product: string;
  count: number;
  mean: number;
  std: number;
  min: number;
  max: number;
  stationary: boolean;
  d: number;
  adf_statistic: number;
  adf_p_value: number;
  missing_before: number;
  missing_after: number;
  outliers_before: number;
  outliers_after: number;
  cleaning_method: string;
  dates: string[];
  sales: number[];
  rolling_mean: number[];
  rolling_std: number[];
  seasonality: SeasonalityCell[];
}

// ── Helper ───────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Request gagal: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Endpoints ────────────────────────────────────────────────────

/** Ambil semua nama produk dari dataset Excel */
export async function getProducts(): Promise<string[]> {
  const data = await apiFetch<{ products: string[] }>("/products");
  return data.products;
}

/**
 * Forecast penjualan untuk 1 produk.
 * @param product  Nama persis dari kolom "Produk" di Excel, misal "5DAYS CHOCO BANANA (40 Pcs)"
 * @param horizon  Berapa minggu ke depan
 */
export async function forecastProduct(
  product: string,
  horizon: number
): Promise<ForecastResponse> {
  return apiFetch<ForecastResponse>("/forecast", {
    method: "POST",
    body: JSON.stringify({ product, horizon }),
  });
}

/** Evaluasi model — train/test split MAE, RMSE, MAPE */
export async function evaluateProduct(
  product: string
): Promise<EvaluationResponse> {
  return apiFetch<EvaluationResponse>("/evaluate", {
    method: "POST",
    body: JSON.stringify({ product }),
  });
}

/** EDA stats + rolling mean untuk 1 produk */
export async function getEDA(product: string): Promise<EDAResponse> {
  return apiFetch<EDAResponse>("/eda", {
    method: "POST",
    body: JSON.stringify({ product }),
  });
}