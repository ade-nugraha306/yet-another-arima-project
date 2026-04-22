"""
arima_service.py
Bridge antara pipeline arima_ta.py dan endpoint FastAPI.
"""

import os
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from functools import lru_cache

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.api import ExponentialSmoothing
from sklearn.metrics import mean_absolute_error, mean_squared_error
from pmdarima import auto_arima

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------
# PATH ke file Excel  (sesuaikan jika perlu)
# ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "AVG 12W & 5W (W1-W40).xlsx"


# ---------------------------------------------------------------
# LOAD + CACHE dataframe (agar tidak re-load tiap request)
# ---------------------------------------------------------------
_df_long_cache: pd.DataFrame | None = None


def _is_week_col(c) -> bool:
    """Cek apakah nama kolom adalah nomor minggu (1–52)."""
    try:
        val = float(str(c).strip())
        return val == int(val) and 1 <= int(val) <= 52
    except Exception:
        return False


def _load_df_long() -> pd.DataFrame:
    global _df_long_cache
    if _df_long_cache is not None:
        return _df_long_cache

    # ── Baca raw dulu untuk cari baris header ───────────────────
    df_raw = pd.read_excel(DATA_PATH, header=None)
    header_row = df_raw[
        df_raw.astype(str).apply(
            lambda x: x.str.contains("Kode Produk", case=False)
        ).any(axis=1)
    ].index[0]

    # ── Baca ulang dengan header yang benar ─────────────────────
    df = pd.read_excel(DATA_PATH, header=header_row)
    df = df.loc[:, ~df.columns.duplicated()]

    # ── Deteksi week cols secara robust ─────────────────────────
    # XLSX punya kolom: 1 (int), 2.0, 3.0, ... (float) → keduanya valid
    # Kolom non-minggu: "Total Result", "AVG 12W", "Adjustment", NaN → diabaikan
    week_cols = [c for c in df.columns if _is_week_col(c)]

    if len(week_cols) == 0:
        raise ValueError(
            f"Tidak ada kolom minggu yang terdeteksi. "
            f"Periksa format file: {DATA_PATH}"
        )

    # ── Pastikan kolom id ada ────────────────────────────────────
    id_cols = ["PRINC 1", "Kode Produk", "Produk"]
    missing_id = [c for c in id_cols if c not in df.columns]
    if missing_id:
        raise ValueError(f"Kolom berikut tidak ditemukan: {missing_id}")

    # ── Buang baris tanpa nama produk ────────────────────────────
    df = df[df["Produk"].notna()].copy()

    # ── Melt ke format long ──────────────────────────────────────
    df_long = df.melt(
        id_vars=id_cols,
        value_vars=week_cols,
        var_name="Week",
        value_name="Sales",
    )

    # Konversi Week ke int (dari int/float) dan Sales ke numeric
    df_long["Week"]  = df_long["Week"].apply(lambda x: int(float(x)))
    df_long["Sales"] = pd.to_numeric(df_long["Sales"], errors="coerce")

    # ── Buat kolom Date dari nomor minggu ────────────────────────
    start_date = pd.Timestamp("2025-01-01")
    df_long["Date"] = df_long["Week"].apply(
        lambda w: start_date + pd.to_timedelta((w - 1) * 7, unit="D")
    )

    df_long = df_long.sort_values(["Produk", "Date"]).reset_index(drop=True)
    _df_long_cache = df_long
    return _df_long_cache


# ---------------------------------------------------------------
# FUNGSI UTILITAS (diambil dari arima_ta.py)
# ---------------------------------------------------------------

def _clean_all_numeric(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    # Hanya bersihkan kolom Sales saja — clipping semua kolom numerik
    # (termasuk Week 1-40) bisa merusak nilai Sales secara tidak langsung
    cleaning_stats = {
        "missing_before": 0,
        "missing_after": 0,
        "outliers_before": 0,
        "outliers_after": 0,
        "method": "Interpolasi linear + IQR clipping (1.5×IQR)",
    }

    if "Sales" not in df.columns:
        return df, cleaning_stats

    cleaning_stats["missing_before"] = int(df["Sales"].isna().sum())
    df["Sales"] = df["Sales"].interpolate(method="linear")
    cleaning_stats["missing_after"] = int(df["Sales"].isna().sum())

    # IQR clipping hanya jika ada variasi cukup (hindari data konstan)
    Q1, Q3 = df["Sales"].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    if IQR > 0:
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        cleaning_stats["outliers_before"] = int(
            ((df["Sales"] < lower_bound) | (df["Sales"] > upper_bound)).sum()
        )
        df["Sales"] = df["Sales"].clip(lower_bound, upper_bound)
        cleaning_stats["outliers_after"] = 0  # by definition setelah clip

    return df, cleaning_stats


def _check_stationarity(series: pd.Series):
    from statsmodels.tsa.stattools import adfuller
    series = series.dropna()
    if series.nunique() <= 1:
        return True, 0.0, 0.0  # stationary, p_value, adf_stat
    try:
        res = adfuller(series, autolag="AIC")
        return res[1] <= 0.05, res[1], res[0]  # stationary, p_value, adf_stat
    except Exception:
        return False, 1.0, 0.0


def _make_stationary(df: pd.DataFrame):
    s = df["Sales"]
    is_stat, _, _ = _check_stationarity(s)
    if is_stat:
        return df, "Sales", 0
    df["Sales_Diff"] = s.diff()
    if _check_stationarity(df["Sales_Diff"].dropna())[0]:
        return df, "Sales_Diff", 1
    df["Sales_Diff2"] = df["Sales_Diff"].diff()
    return df, "Sales_Diff2", 2


def _stable_forecast(series: pd.Series, order=None, steps: int = 5) -> pd.Series:
    series = pd.Series(series).dropna()
    if len(series) < 3:
        return pd.Series([float(series.iloc[-1])] * steps)

    # 1) ARIMA
    if order is not None:
        try:
            model = ARIMA(series, order=order).fit()
            fc = model.forecast(steps=steps)
            return pd.Series(fc.values)
        except Exception:
            pass

    # 2) ETS fallback
    try:
        ets = ExponentialSmoothing(series, trend="add", seasonal=None, damped=True).fit()
        return pd.Series(ets.forecast(steps).values)
    except Exception:
        pass

    # 3) Naive fallback
    return pd.Series([float(series.iloc[-1])] * steps)

def _get_confidence_intervals(
    series: pd.Series,
    order,
    steps: int,
    forecast_values=None,
):
    """CI 95% business-safe: selalu di-anchor ke forecast_values (WMA atau ARIMA).

    Perubahan utama:
    - Menerima forecast_values dari luar agar CI sinkron dengan forecast final
      (termasuk saat model buruk dan forecast diganti WMA).
    - Spread dihitung dari sigma historis — bukan persentase flat — sehingga
      lower/upper ikut naik/turun mengikuti forecast, bukan flat atau turun.
    - Spread membesar seiring horizon (sqrt scaling, seperti random-walk).
    """
    series = pd.Series(series).dropna()

    # ── Volatilitas historis sebagai base spread ─────────────────────────────
    roll_std = series.rolling(4, min_periods=2).std().iloc[-1]
    sigma = float(roll_std if not np.isnan(roll_std) else series.std())
    sigma = max(sigma, 1e-6)

    # ── Gunakan forecast_values kalau ada, fallback ke ARIMA ────────────────
    if forecast_values is not None:
        fc = np.asarray(forecast_values, dtype=float)
    else:
        try:
            model = ARIMA(series, order=order).fit()
            fc = model.get_forecast(steps=steps).predicted_mean.values
        except Exception:
            fc = _stable_forecast(series, order=order, steps=steps).values

    # ── Cap sigma relatif ke mean forecast agar CI tidak absurd ────────────
    # Kalau data historis punya outlier besar, sigma mentah bisa jauh lebih besar
    # dari nilai forecast yang kecil → lower langsung negatif.
    mean_fc = float(np.mean(fc)) if len(fc) > 0 else 1.0
    # Cap: sigma tidak boleh lebih dari 20% rata-rata forecast
    sigma_used = min(sigma, 0.20 * mean_fc) if mean_fc > 0 else sigma

    # ── Bangun CI relatif ke fc, spread membesar seiring horizon ────────────
    # Floor: lower tidak boleh < 45% forecast.
    # Dipilih karena di ratio ini lower secara natural monotonic naik mengikuti
    # forecast tanpa perlu enforce tambahan — cukup max(f-hw, 0.45*f).
    LOWER_FLOOR_RATIO = 0.45

    upper = []
    lower = []

    for i, f in enumerate(fc):
        hw = 1.96 * sigma_used * np.sqrt(i + 1)

        u = f + hw
        l = max(f - hw, LOWER_FLOOR_RATIO * f, 0.0)

        upper.append(float(u))
        lower.append(float(l))

    return upper, lower

def _prepare_product(product_name: str):
    """Load, clean & stationarize data untuk 1 produk."""
    df_long = _load_df_long()
    df_p = df_long[df_long["Produk"] == product_name].copy()
    if df_p.empty:
        raise ValueError(f"Produk '{product_name}' tidak ditemukan.")
    df_p = df_p.set_index("Date").sort_index()
    df_p, cleaning_stats = _clean_all_numeric(df_p)
    df_p, col_used, d = _make_stationary(df_p)
    return df_p, col_used, d, cleaning_stats


# ---------------------------------------------------------------
# PUBLIC API  (dipanggil oleh app.py)
# ---------------------------------------------------------------

def get_products() -> list[str]:
    df_long = _load_df_long()
    return sorted(df_long["Produk"].dropna().unique().tolist())


def _invert_differencing(fc_diff: pd.Series, last_values: dict, d: int) -> pd.Series:
    """
    Kembalikan hasil forecast dari skala differencing ke skala Sales asli.
    - d=0: tidak perlu invert
    - d=1: cumsum dari last Sales
    - d=2: cumsum dua kali (last Sales + last Sales_Diff)
    """
    if d == 0:
        return fc_diff

    fc = fc_diff.values.copy().astype(float)

    if d >= 1:
        last_sales = float(last_values["Sales"])
        # Invert diff-1: nilai forecast = last_sales + cumsum(diff_forecast)
        reverted = np.empty(len(fc))
        prev = last_sales
        for i, v in enumerate(fc):
            prev = prev + v
            reverted[i] = prev
        fc = reverted

    if d >= 2:
        # Invert diff-2: butuh last Sales dan last Sales_Diff
        last_diff = float(last_values.get("Sales_Diff", 0.0))
        reverted2 = np.empty(len(fc))
        prev_sales = last_sales
        prev_diff  = last_diff
        for i, v in enumerate(fc_diff.values):
            prev_diff  = prev_diff + v          # invert diff-2 → diff-1
            prev_sales = prev_sales + prev_diff  # invert diff-1 → Sales
            reverted2[i] = prev_sales
        fc = reverted2

    return pd.Series(fc)

def run_forecast(product: str, horizon: int = 5) -> dict:
    df_p, col_used, d, _cleaning_stats = _prepare_product(product)

    sales_series = df_p["Sales"].copy()

    # ── HANDLE MISSING ─────────────────────────
    sales_series = sales_series.interpolate()
    sales_series = sales_series.bfill().ffill()

    # ── VALIDASI DATA ─────────────────────────
    if len(sales_series.dropna()) < 10:
        raise ValueError("Data terlalu sedikit / terlalu banyak missing")

    last_sales = float(sales_series.iloc[-1])

    # ── AUTO ARIMA ────────────────────────────
    try:
        am = auto_arima(
            sales_series,
            start_p=1,
            start_q=1,
            max_p=3,
            max_q=3,
            d=1,  # paksa differencing
            seasonal=False,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore"
        )
        order = am.order
        aic = float(am.aic())
    except Exception:
        order = (1, 1, 1)
        aic = None

    # ── FORECAST ARIMA ────────────────────────
    fc_series = _stable_forecast(sales_series, order=order, steps=horizon)

    # ── DETEKSI MODEL JELEK ───────────────────
    is_flat = len(set([round(v, 3) for v in fc_series])) == 1
    is_bad_model = order in [(0,0,0), (0,1,0)]

    # ── FALLBACK MOVING AVERAGE ───────────────
    if is_flat or is_bad_model:
        fc_series = weighted_moving_average(sales_series, horizon)

    # ── CLAMP NEGATIVE ────────────────────────
    fc_series = np.maximum(fc_series, 0)

    # ── CONFIDENCE INTERVAL (anchor ke fc_series final) ───────────
    upper, lower = _get_confidence_intervals(
        sales_series, order, horizon, forecast_values=fc_series
    )

    return {
        "forecast":   [round(float(v), 4) for v in fc_series],
        "upper":      [round(float(v), 4) for v in upper],
        "lower":      [round(float(v), 4) for v in lower],
        "order":      list(order),
        "aic":        round(aic, 4) if aic is not None else None,
        "weeks":      [f"F+{i+1}" for i in range(horizon)],
        "last_sales": round(last_sales, 4),
    }

def run_evaluation(product: str) -> dict:
    """
    Train/test split evaluation untuk 1 produk.
    Returns:
      {
        mae, rmse, mape,
        actual_train: list[float],
        actual_test:  list[float],
        fitted:       list[float],
        order: [p, d, q],
        dates_train: list[str],
        dates_test:  list[str],
      }
    """
    df_p, col_used, d, _cleaning_stats = _prepare_product(product)
    sales_series = df_p["Sales"].dropna()

    n = len(sales_series)
    if n < 10:
        raise ValueError(f"Data terlalu pendek untuk produk '{product}' (n={n}).")

    # Auto ARIMA pada Sales asli
    try:
        am = auto_arima(
            sales_series,
            start_p=0, start_q=0,
            max_p=3, max_q=3,
            max_d=2,
            seasonal=False,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            maxiter=30,
        )
        order = am.order
        aic = float(am.aic())
    except Exception:
        order = (1, d, 1)
        aic = None

    # Train/test split (75/25) — semua pakai Sales asli
    train_size  = int(0.75 * n)
    train_sales = sales_series[:train_size]
    test_sales  = sales_series[train_size:]

    fc = _stable_forecast(train_sales, order=order, steps=len(test_sales))

    mae  = float(mean_absolute_error(test_sales, fc))
    rmse = float(np.sqrt(mean_squared_error(test_sales, fc)))
    mape = float(np.mean(np.abs((test_sales.values - fc.values) / (test_sales.values + 1e-10))) * 100)

    def _to_dates(idx):
        try:
            return [str(i.date()) for i in idx]
        except Exception:
            return [str(i) for i in idx]

    return {
        "order":        list(order),
        "aic":          round(aic, 4) if aic is not None else None,
        "mae":          round(mae, 4),
        "rmse":         round(rmse, 4),
        "mape":         round(mape, 4),
        "actual_train": [round(float(v), 4) for v in train_sales],
        "actual_test":  [round(float(v), 4) for v in test_sales],
        "fitted":       [round(float(v), 4) for v in fc],
        "dates_train":  _to_dates(train_sales.index),
        "dates_test":   _to_dates(test_sales.index),
    }


# Mapping week number → nama bulan (konsisten dengan start_date 2025-01-01)
_WEEK_TO_MONTH = {
    w: pd.Timestamp("2025-01-01") + pd.to_timedelta((w - 1) * 7, unit="D")
    for w in range(1, 53)
}


def _build_seasonality(product: str) -> list[dict]:
    """
    Agregasi rata-rata Sales per (bulan, minggu-dalam-bulan) dari data mentah.
    Menggunakan kolom Week asli dari df_long — bukan derived dari Date —
    sehingga konsisten dengan struktur Excel.

    Return: list of { month, week_in_month, avg_sales }
    """
    df_long = _load_df_long()
    df_p = df_long[df_long["Produk"] == product][["Week", "Sales"]].copy()
    df_p["Sales"] = pd.to_numeric(df_p["Sales"], errors="coerce")
    df_p = df_p.dropna(subset=["Sales"])

    df_p["_date"]          = df_p["Week"].map(_WEEK_TO_MONTH)
    df_p["_month_num"]     = df_p["_date"].dt.month
    df_p["_month_label"]   = df_p["_date"].dt.strftime("%b")
    df_p["_week_in_month"] = df_p["Week"].apply(
        lambda w: f"W{((w - 1) % 4) + 1}"
    )

    grouped = (
        df_p.groupby(["_month_num", "_month_label", "_week_in_month"], sort=True)["Sales"]
        .mean()
        .reset_index()
    )

    return [
        {
            "month":         row["_month_label"],
            "week_in_month": row["_week_in_month"],
            "avg_sales":     round(float(row["Sales"]), 4),
        }
        for _, row in grouped.iterrows()
    ]

def run_eda(product: str) -> dict:
    """
    Basic EDA stats + rolling mean untuk 1 produk.
    Returns dict berisi statistik & data untuk plot.
    """
    df_p, col_used, d, cleaning_stats = _prepare_product(product)
    s = df_p["Sales"].dropna()

    is_stationary, adf_p_value, adf_statistic = _check_stationarity(s)

    rolling_mean = s.rolling(window=4, min_periods=1).mean()
    rolling_std  = s.rolling(window=4, min_periods=1).std().fillna(0)

    def _to_dates(idx):
        try:
            return [str(i.date()) for i in idx]
        except Exception:
            return [str(i) for i in idx]

    return {
        "product":          product,
        "count":            int(len(s)),
        "mean":             round(float(s.mean()), 4),
        "std":              round(float(s.std()), 4),
        "min":              round(float(s.min()), 4),
        "max":              round(float(s.max()), 4),
        "stationary":       bool(is_stationary),
        "d":                d,
        "adf_statistic":    round(float(adf_statistic), 4),
        "adf_p_value":      round(float(adf_p_value), 4),
        "missing_before":   cleaning_stats["missing_before"],
        "missing_after":    cleaning_stats["missing_after"],
        "outliers_before":  cleaning_stats["outliers_before"],
        "outliers_after":   cleaning_stats["outliers_after"],
        "cleaning_method":  cleaning_stats["method"],
        "dates":            _to_dates(s.index),
        "sales":            [round(float(v), 4) for v in s],
        "rolling_mean":     [round(float(v), 4) for v in rolling_mean],
        "rolling_std":      [round(float(v), 4) for v in rolling_std],
        "seasonality":      _build_seasonality(product),
    }

def moving_average_forecast(series, steps=5, window=3):
    ma = series.rolling(window=window).mean().iloc[-1]
    return [float(ma)] * steps

def weighted_moving_average(series, steps=5):
    weights = np.arange(1, 4)  # [1,2,3]
    last_vals = series.tail(3).values

    if len(last_vals) < 3:
        return [float(series.iloc[-1])] * steps

    wma = np.dot(last_vals, weights) / weights.sum()

    # bikin sedikit trend biar ga flat
    trend = (last_vals[-1] - last_vals[0]) / len(last_vals)

    return [float(wma + i * trend) for i in range(1, steps+1)]