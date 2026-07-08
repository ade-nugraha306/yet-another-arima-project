// src/services/api.ts
// All requests go through /api/* → Vite proxy → http://localhost:8000
// New family-level endpoints per TA Final Methodology

const BASE_URL = "/api";

// ── Helper ────────────────────────────────────────────────────

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

// ── Types ─────────────────────────────────────────────────────

export interface DataAcquisitionResponse {
  family: string;
  sku_count: number;
  skus: string[];
  total_weeks: number;
  weeks: string[];
  sales_raw: (number | null)[];
}

export interface DataPreparationResponse {
  family: string;
  missing_before: number;
  missing_after: number;
  outliers_before: number;
  outliers_after: number;
  cleaning_method: string;
  adf_statistic_before: number;
  adf_p_value_before: number;
  adf_statistic_after: number;
  adf_p_value_after: number;
  stationary_before: boolean;
  stationary_after: boolean;
  d: number;
  weeks: string[];
  sales_before: (number | null)[];
  sales_after: number[];
}

export interface EDAResponse {
  family: string;
  count: number;
  mean: number;
  std: number;
  min: number;
  max: number;
  stationary: boolean;
  adf_statistic: number;
  adf_p_value: number;
  missing_before: number;
  missing_after: number;
  outliers_before: number;
  outliers_after: number;
  cleaning_method: string;
  weeks: string[];
  sales_before: (number | null)[];
  sales_after: number[];
  rolling_mean: number[];
  rolling_std: number[];
  boxplot_before: BoxplotStats;
  boxplot_after: BoxplotStats;
}

export interface BoxplotStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
}

export interface ModellingResponse {
  family: string;
  order: [number, number, number];
  aic: number | null;
  horizon: number;
  forecast: number[];
  upper: number[];
  lower: number[];
  forecast_dates: string[];
  last_sales: number;
  historical_weeks: string[];
  historical_sales: number[];
}

export interface EvaluationResponse {
  family: string;
  order: [number, number, number];
  aic: number | null;
  mae: number;
  rmse: number;
  smape: number;        // sMAPE — not MAPE
  actual_train: number[];
  actual_test: number[];
  fitted: number[];
  dates_train: string[];
  dates_test: string[];
  trend: "FAST" | "MEDIUM" | "SLOW";
}

// ── Endpoints ─────────────────────────────────────────────────

/** Return all valid product families from the dataset */
export async function getFamilies(): Promise<string[]> {
  const data = await apiFetch<{ families: string[] }>("/families");
  return data.families;
}

/** Raw data acquisition for a family */
export async function getDataAcquisition(family: string): Promise<DataAcquisitionResponse> {
  return apiFetch<DataAcquisitionResponse>(
    `/data-acquisition?family=${encodeURIComponent(family)}`
  );
}

/** Cleaning pipeline results for a family */
export async function getDataPreparation(family: string): Promise<DataPreparationResponse> {
  return apiFetch<DataPreparationResponse>(
    `/data-preparation?family=${encodeURIComponent(family)}`
  );
}

/** EDA data for a family (before & after cleaning) */
export async function getEDA(family: string): Promise<EDAResponse> {
  return apiFetch<EDAResponse>(`/eda?family=${encodeURIComponent(family)}`);
}

/** Run ARIMA modelling and get forecast for a family */
export async function getModelling(
  family: string,
  horizon: number
): Promise<ModellingResponse> {
  return apiFetch<ModellingResponse>(
    `/modelling?family=${encodeURIComponent(family)}&horizon=${horizon}`
  );
}

/** Evaluation metrics (MAE, RMSE, sMAPE) + trend classification for a family */
export async function getEvaluation(family: string): Promise<EvaluationResponse> {
  return apiFetch<EvaluationResponse>(
    `/evaluation?family=${encodeURIComponent(family)}`
  );
}
