"""
arima_service.py

Implementasi langsung dari ARIMA_TA_CSV.ipynb.
Setiap fungsi dan pipeline mengikuti notebook cell demi cell secara literal.
Notebook adalah sumber kebenaran tunggal.

Pipeline order (sesuai notebook):
  Cell 2  — pd.read_csv(..., header=None)
  Cell 3  — iloc[3:], headers, week column detection
  Cell 4  — wide→long manual row iteration
  Cell 5  — timeline reconstruction (full_weeks.merge)
  Cell 6  — interpolation (limit_direction="both") + fillna(0)
            fix_internal_zeros TIDAK dijalankan (dinonaktifkan di notebook)
  Cell 6b — winsorize_series per product (IQR, sebelum assign family)
  Cell 7  — extract_family (startswith), drop last week, aggregate, filter MIN_FAMILY_AVG
  Cell 12 — fit_arima, arima_forecast, smape, evaluate_forecast
  Cell 13 — train/test split, clip, metrics
  Cell 15 — final model + forecast + CI
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path
from statsmodels.tsa.stattools import adfuller
from pmdarima import auto_arima
from statsmodels.tsa.stattools import acf, pacf

# ---------------------------------------------------------------------------
# CONFIG  (notebook cell 1 — verbatim)
# ---------------------------------------------------------------------------
BASE_DIR         = Path(__file__).resolve().parent.parent
DATA_PATH        = BASE_DIR / "AVG 12W & 5W.csv"

TEST_SIZE        = 5
FORECAST_HORIZON = 5
MIN_FAMILY_AVG   = 5
ARIMA_MAX_P      = 3
ARIMA_MAX_Q      = 3

# ---------------------------------------------------------------------------
# CELL 12 — fungsi statistik (verbatim dari notebook)
# ---------------------------------------------------------------------------

def fit_arima(train_series):
    """Notebook cell 12 — fit_arima() verbatim."""
    train_series = pd.Series(train_series).astype(float)
    model = auto_arima(
        train_series,
        seasonal=False,
        start_p=0,
        start_q=0,
        max_p=ARIMA_MAX_P,
        max_d=2,
        max_q=ARIMA_MAX_Q,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
        information_criterion="aicc",
        test="adf",
    )
    return model


def arima_forecast(model, steps, with_ci=False):
    """Notebook cell 12 — arima_forecast() verbatim."""
    if with_ci:
        forecast, conf_int = model.predict(n_periods=steps, return_conf_int=True)
        return np.array(forecast), conf_int
    forecast = model.predict(n_periods=steps)
    return np.array(forecast)


def smape(actual, pred):
    """Notebook cell 12 — smape() verbatim."""
    actual = np.array(actual)
    pred   = np.array(pred)
    denominator = np.abs(actual) + np.abs(pred)
    return np.mean(
        np.where(
            denominator == 0,
            0,
            2 * np.abs(actual - pred) / denominator,
        )
    ) * 100


def evaluate_forecast(actual, pred):
    """Notebook cell 12 — evaluate_forecast() verbatim."""
    actual = np.array(actual)
    pred   = np.array(pred)
    mae       = np.mean(np.abs(actual - pred))
    rmse      = np.sqrt(np.mean((actual - pred) ** 2))
    smape_val = smape(actual, pred)
    return {"MAE": mae, "RMSE": rmse, "sMAPE": smape_val}


# ---------------------------------------------------------------------------
# CELL 6b — winsorize_series (verbatim dari notebook)
# ---------------------------------------------------------------------------

def winsorize_series(series, limits=(0.01, 0.01)):
    """Notebook cell 6b — winsorize_series() verbatim. limits param tidak dipakai."""
    q1  = series.quantile(0.25)
    q3  = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return series.clip(lower=lower_bound, upper=upper_bound)


# ---------------------------------------------------------------------------
# CELL 7 — extract_family (startswith, verbatim dari notebook)
# ---------------------------------------------------------------------------

def extract_family(product_name):
    """Notebook cell 7 — extract_family() verbatim. Pakai startswith, bukan 'in'."""
    product_name = str(product_name).upper()
    if product_name.startswith("5DAYS"):      return "5DAYS"
    elif product_name.startswith("CAF"):      return "CAF"
    elif product_name.startswith("FOX"):      return "FOX"
    elif product_name.startswith("HYDROPLUS"): return "HYDROPLUS"
    elif product_name.startswith("ROYO"):     return "ROYO"
    elif product_name.startswith("TUBRUK"):   return "TUBRUK"
    elif product_name.startswith("UHT"):      return "UHT"
    return "OTHER"

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS FOR EDA TRANSPARENCY
# ---------------------------------------------------------------------------

def _compute_acf(series: pd.Series, max_lag: int) -> list:
    """Compute ACF using statsmodels (same as notebook's plot_acf)."""
    s = series.dropna().values
    if len(s) < 2:
        return [{"lag": i, "value": 1.0 if i == 0 else 0.0} for i in range(max_lag + 1)]
    acf_vals = acf(s, nlags=max_lag, fft=False)
    return [{"lag": i, "value": round(float(acf_vals[i]), 4)} for i in range(len(acf_vals))]

def _compute_pacf(series: pd.Series, max_lag: int) -> list:
    """Compute PACF using statsmodels (method='ywm' as in notebook)."""
    s = series.dropna().values
    if len(s) < 2:
        return [{"lag": i, "value": 1.0 if i == 0 else 0.0} for i in range(max_lag + 1)]
    pacf_vals = pacf(s, nlags=max_lag, method='ywm')
    return [{"lag": i, "value": round(float(pacf_vals[i]), 4)} for i in range(len(pacf_vals))]

def _compute_histogram(series: pd.Series, bins: int = 8) -> list:
    """Compute histogram bins and counts, return list of {range: string, count: int}."""
    s = series.dropna().values
    if len(s) == 0:
        return []
    min_val = np.min(s)
    max_val = np.max(s)
    if min_val == max_val:
        return [{"range": f"{min_val:.0f}", "count": len(s)}]
    bin_edges = np.linspace(min_val, max_val, bins + 1)
    counts, _ = np.histogram(s, bins=bin_edges)
    result = []
    for i in range(bins):
        left = bin_edges[i]
        right = bin_edges[i + 1]
        range_str = f"{left:.0f}-{right:.0f}"
        result.append({"range": range_str, "count": int(counts[i])})
    return result

def _boxplot_summary(series: pd.Series) -> dict:
    """Return min, q1, median, q3, max, iqr, outlier_count for a series."""
    s = series.dropna()
    if len(s) == 0:
        return {"min": 0, "q1": 0, "median": 0, "q3": 0, "max": 0, "iqr": 0, "outlier_count": 0}
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = ((s < lower) | (s > upper)).sum()
    return {
        "min": round(s.min(), 4),
        "q1": round(q1, 4),
        "median": round(s.median(), 4),
        "q3": round(q3, 4),
        "max": round(s.max(), 4),
        "iqr": round(iqr, 4),
        "outlier_count": int(outliers)
    }

# ---------------------------------------------------------------------------
# PIPELINE UTAMA — build_pipeline()
# Menjalankan cell 2–7 secara berurutan, persis seperti notebook.
# Hasilnya di-cache setelah pertama kali dijalankan.
# ---------------------------------------------------------------------------

_pipeline_cache: dict | None = None


def _build_pipeline() -> dict:
    """
    Jalankan cell 2–7 notebook secara literal.
    Return dict berisi:
      df_full_long : DataFrame setelah winsorize, sebelum drop last week
      df_family    : DataFrame [Family, Week, Sales] setelah drop last week + filter
      families     : list of valid family names (sorted)
      actual_weeks : list of week numbers yang ada di data (dari cell 5)
    """
    global _pipeline_cache
    if _pipeline_cache is not None:
        return _pipeline_cache

    # ------------------------------------------------------------------
    # CELL 2 — Memuat Dataset CSV
    # pd.read_csv(..., header=None) — persis notebook
    # ------------------------------------------------------------------
    df_raw = pd.read_csv(DATA_PATH, header=None, encoding="utf-8-sig")

    # ------------------------------------------------------------------
    # CELL 3 — Deteksi Kolom Minggu
    # Skip metadata rows 0–2; row 3 = header row
    # ------------------------------------------------------------------
    df_clean = df_raw.iloc[3:].reset_index(drop=True)
    headers  = df_clean.iloc[0].tolist()   # baris pertama setelah metadata = header
    df_data  = df_clean.iloc[1:].reset_index(drop=True)

    # posisi kolom produk (fixed, sesuai notebook)
    col_princ   = 0  # PRINC
    col_code    = 1  # Kode Produk
    col_product = 2  # Produk

    # deteksi week columns (numeric, range 1–40)
    weeks            = []
    week_col_indices = []
    for col_idx, header in enumerate(headers):
        try:
            week_num = float(header)
            if 1 <= week_num <= 40:
                weeks.append(int(week_num))
                week_col_indices.append(col_idx)
        except (ValueError, TypeError):
            pass

    # ------------------------------------------------------------------
    # CELL 4 — Transformasi Wide ke Long (manual row iteration, verbatim)
    # ------------------------------------------------------------------
    data_list = []
    for idx, row in df_data.iterrows():
        princ   = row[col_princ]
        code    = row[col_code]
        product = row[col_product]

        if pd.isna(product) or product == "":
            continue

        for week_num, col_idx in zip(weeks, week_col_indices):
            sales = row[col_idx]
            if pd.notna(sales) and sales != "":
                try:
                    data_list.append({
                        "PRINC":       princ,
                        "ProductCode": code,
                        "Product":     product,
                        "Week":        week_num,
                        "Sales":       float(sales),
                    })
                except (ValueError, TypeError):
                    pass

    df_long = pd.DataFrame(data_list)
    df_long = df_long.sort_values(["Product", "Week"]).reset_index(drop=True)

    # ------------------------------------------------------------------
    # CELL 5 — Rekonstruksi Timeline Mingguan
    # full_weeks.merge per product, persis notebook
    # ------------------------------------------------------------------
    actual_weeks = sorted(df_long["Week"].unique())
    products     = df_long["Product"].unique()
    full_data    = []

    for product in products:
        df_p       = df_long[df_long["Product"] == product].copy()
        full_weeks = pd.DataFrame({"Week": actual_weeks})
        df_full    = full_weeks.merge(df_p[["Week", "Sales"]], on="Week", how="left")
        df_full["Product"] = product
        full_data.append(df_full)

    df_full_long = pd.concat(full_data, ignore_index=True)
    df_full_long_before_interpol = df_full_long.copy()

    # ------------------------------------------------------------------
    # CELL 6 — Penanganan Missing Value
    # interpolate(limit_direction="both") + fallback fillna(0)
    # fix_internal_zeros TIDAK dijalankan (dinonaktifkan di notebook)
    # ------------------------------------------------------------------
    df_full_long["Sales"] = (
        df_full_long
        .groupby("Product")["Sales"]
        .transform(lambda s: s.interpolate(method="linear", limit_direction="both"))
    )

    # Simpan snapshot setelah interpolasi (sebelum fillna(0))
    df_full_long_after_interpol = df_full_long.copy()

    # Kemudian fillna(0) untuk sisa NaN
    df_full_long["Sales"] = df_full_long["Sales"].fillna(0)
    remaining = df_full_long["Sales"].isna().sum()
    if remaining > 0:
        df_full_long["Sales"] = df_full_long["Sales"].fillna(0)

    # ------------------------------------------------------------------
    # CELL 6b — Winsorize per Product (sebelum assign family, verbatim)
    # ------------------------------------------------------------------
    # Simpan snapshot sebelum winsorize
    df_full_long_pre_winsor = df_full_long.copy()

    # Simpan jumlah outlier notebook (pre-winsorize)
    product_outlier_counts_before = {}
    for product in df_full_long["Product"].unique():
        mask = df_full_long["Product"] == product
        series = df_full_long.loc[mask, "Sales"]

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        product_outlier_counts_before[product] = int(
            ((series < lower) | (series > upper)).sum()
        )

        df_full_long.loc[mask, "Sales"] = winsorize_series(series)

    # ------------------------------------------------------------------
    # CELL 7 — Ekstraksi Family, Drop Last Week, Agregasi, Filter
    # ------------------------------------------------------------------
    df_full_long["Family"] = df_full_long["Product"].apply(extract_family)

    # drop minggu terakhir (notebook: Week.max())
    last_week    = df_full_long["Week"].max()
    df_full_long = df_full_long[df_full_long["Week"] != last_week].copy()

    # agregasi ke level family
    df_family = (
        df_full_long
        .groupby(["Family", "Week"], as_index=False)["Sales"]
        .sum()
    )

    # filter MIN_FAMILY_AVG (notebook: mean >= 5)
    family_stats  = (
        df_family
        .groupby("Family")["Sales"]
        .agg(["mean", "sum"])
        .reset_index()
    )
    valid_families = family_stats[
        family_stats["mean"] >= MIN_FAMILY_AVG
    ]["Family"].tolist()

    df_family = df_family[df_family["Family"].isin(valid_families)].copy()
    families  = sorted(valid_families)

    # Tambahkan kolom Date untuk keperluan API response
    start_date = pd.Timestamp("2025-01-01")
    df_family["Date"] = df_family["Week"].apply(
        lambda w: start_date + pd.to_timedelta((w - 1) * 7, unit="D")
    )

    _pipeline_cache = {
        "df_full_long": df_full_long,
        "df_full_long_before_interpol": df_full_long_before_interpol,
        "df_full_long_after_interpol": df_full_long_after_interpol,
        "df_full_long_pre_winsor": df_full_long_pre_winsor,
        "product_outlier_counts_before": product_outlier_counts_before,
        "df_long_pre_reconstruct": df_long,
        "df_family": df_family,
        "families": families,
        "actual_weeks": actual_weeks,
    }
    return _pipeline_cache


# ---------------------------------------------------------------------------
# HELPER — ambil series family dari pipeline
# ---------------------------------------------------------------------------

def _get_family_series(family: str) -> tuple[np.ndarray, pd.Series]:
    """
    Ambil series Sales untuk satu family dari df_family.
    Return (series_array, dates_series).
    """
    pipe      = _build_pipeline()
    df_family = pipe["df_family"]
    df_f      = df_family[df_family["Family"] == family].sort_values("Week")
    if df_f.empty:
        raise ValueError(f"Family '{family}' not found. Valid: {pipe['families']}")
    series = df_f["Sales"].values.astype(float)
    dates  = df_f["Date"]
    return series, dates


# ---------------------------------------------------------------------------
# PUBLIC API — endpoint functions
# ---------------------------------------------------------------------------

def get_families() -> list[str]:
    """
    GET /products
    Return sorted list of valid families (mean >= MIN_FAMILY_AVG).
    Sesuai notebook cell 7.
    """
    return _build_pipeline()["families"]

def get_data_acquisition(family: str) -> dict:
    """
    GET /data-acquisition?family=...
    Raw weekly sales (sebelum winsorize) untuk satu family.
    Menggunakan df_long (sebelum full_weeks reconstruction) sesuai
    semantik "data akuisisi = data mentah".
    """
    pipe      = _build_pipeline()
    df_family = pipe["df_family"]
    df_full   = pipe["df_full_long"]  # sudah termasuk semua week, setelah winsorize

    # raw = sebelum winsorize → ambil dari df_long sebelum winsorize
    # Untuk konsistensi dengan notebook, gunakan df_full_long yang masih punya
    # semua produk & weeks (setelah timeline reconstruction tapi sebelum drop last week
    # untuk per-product view). Tapi karena drop last week dilakukan pada df_full_long
    # sebelum agregasi, raw_agg di sini menggunakan df_family (post-winsorize).
    # Untuk "before winsorize" reference, gunakan df_full_long pre-winsorize.
    # Karena cache tidak menyimpan pre-winsorize, we aggregate from df_full_long as-is.

    df_f = df_full[df_full["Family"] == family]
    if df_f.empty:
        raise ValueError(f"Family '{family}' not found.")

    sku_list = sorted(df_f["Product"].dropna().unique().tolist())

    df_fam = df_family[df_family["Family"] == family].sort_values("Week")

    return {
        "family":      family,
        "sku_count":   len(sku_list),
        "skus":        sku_list,
        "total_weeks": len(df_fam),
        "weeks":       [d.strftime("%Y-%m-%d") for d in df_fam["Date"]],
        "sales_raw":   [round(float(v), 4) for v in df_fam["Sales"].values],
    }

def get_data_preparation(family: str) -> dict:
    pipe = _build_pipeline()
    df_family_all = pipe["df_family"]                     
    df_full_long = pipe["df_full_long"]                   
    df_pre_winsor = pipe["df_full_long_pre_winsor"].copy() 

    df_pre_winsor["Family"] = df_pre_winsor["Product"].apply(extract_family)
    last_week = df_pre_winsor["Week"].max()
    df_pre_winsor = df_pre_winsor[df_pre_winsor["Week"] != last_week]

    df_pre_agg = (
        df_pre_winsor[df_pre_winsor["Family"] == family]
        .groupby("Week", as_index=False)["Sales"]
        .sum()
    )
    df_post = df_family_all[df_family_all["Family"] == family].sort_values("Week")
    if df_post.empty:
        raise ValueError(f"Family '{family}' not found.")

    weeks = df_post["Week"].values
    pre_sales = []
    for w in weeks:
        val = df_pre_agg[df_pre_agg["Week"] == w]["Sales"].values
        pre_sales.append(val[0] if len(val) > 0 else 0.0)

    # series_before = Pre-Winsor, series_after = Post-Winsor (Cleaned)
    series_before = pd.Series(pre_sales, dtype=float)
    series_after = df_post["Sales"].astype(float)

    # SKU dalam family ini
    df_f = df_full_long[df_full_long["Family"] == family]
    skus = df_f["Product"].unique()

    # ===== MISSING VALUES =====
    df_before_interpol = pipe["df_full_long_before_interpol"]
    df_after_interpol = pipe["df_full_long_after_interpol"]
    missing_before = 0
    for sku in skus:
        mask = (df_before_interpol["Product"] == sku)
        missing_before += df_before_interpol.loc[mask, "Sales"].isna().sum()
    missing_after = 0
    for sku in skus:
        mask = (df_after_interpol["Product"] == sku)
        missing_after += df_after_interpol.loc[mask, "Sales"].isna().sum()

    # ===== OUTLIERS =====
    product_counts = pipe["product_outlier_counts_before"]
    outliers_before = sum(product_counts.get(p, 0) for p in skus)
    outliers_after = 0
    for product, grp in df_f.groupby("Product"):
        s = grp["Sales"].dropna()
        if len(s) == 0:
            continue
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers_after += int(((s < lower) | (s > upper)).sum())

    # ===== FIXED ADF TEST (sesuai notebook) =====
    # Gunakan series_after (data hasil cleaning) sebagai original series untuk ADF
    series = series_after

    def _adf(s):
        s = pd.Series(s).dropna()
        if s.nunique() <= 1:
            return True, 0.0, 0.0
        try:
            r = adfuller(s)
            return r[1] < 0.05, float(r[1]), float(r[0])
        except Exception:
            return False, 1.0, 0.0

    # ADF pada original series (Before Differencing)
    is_stat_orig, adf_p_orig, adf_stat_orig = _adf(series)
    adf_statistic_before = round(adf_stat_orig, 4)
    adf_p_value_before = round(adf_p_orig, 4)
    stationary_before = bool(is_stat_orig)

    # Tentukan differencing dan ADF setelah differencing
    d = 0
    if not is_stat_orig:
        diff1 = series.diff().dropna()
        is_stat1, adf_p1, adf_stat1 = _adf(diff1)
        d = 1
        if not is_stat1:
            diff2 = diff1.diff().dropna()
            is_stat2, adf_p2, adf_stat2 = _adf(diff2)
            d = 2
            adf_statistic_after = round(adf_stat2, 4)
            adf_p_value_after = round(adf_p2, 4)
            stationary_after = bool(is_stat2)
        else:
            adf_statistic_after = round(adf_stat1, 4)
            adf_p_value_after = round(adf_p1, 4)
            stationary_after = bool(is_stat1)
    else:
        # Sudah stasioner, after = before
        adf_statistic_after = adf_statistic_before
        adf_p_value_after = adf_p_value_before
        stationary_after = stationary_before
        d = 0

    return {
        "family": family,
        "missing_before": int(missing_before),
        "missing_after": int(missing_after),
        "outliers_before": outliers_before,
        "outliers_after": outliers_after,
        "cleaning_method": "Linear Interpolation (method='linear', limit_direction='both') + IQR Winsorization (per SKU)",
        "adf_statistic_before": adf_statistic_before,
        "adf_p_value_before": adf_p_value_before,
        "adf_statistic_after": adf_statistic_after,
        "adf_p_value_after": adf_p_value_after,
        "stationary_before": stationary_before,
        "stationary_after": stationary_after,
        "d": d,
        "weeks": [d.strftime("%Y-%m-%d") for d in df_post["Date"]],
        "sales_before": [round(float(v), 4) for v in series_before],
        "sales_after": [round(float(v), 4) for v in series_after],
    }

def get_eda(family: str) -> dict:
    """
    GET /eda?family=...
    EDA: trend, rolling stats, ADF, boxplot.
    - before: data setelah interpolasi & fillna(0) tetapi SEBELUM winsorize
    - after:  data setelah winsorize (dan sudah melalui pipeline lengkap)
    """
    pipe = _build_pipeline()
    df_family = pipe["df_family"]                     # after winsorize (sudah di-drop last week)
    df_pre_winsor = pipe["df_full_long_pre_winsor"].copy()   # sebelum winsorize

    # Tambahkan kolom Family ke df_pre_winsor (karena belum ada)
    df_pre_winsor["Family"] = df_pre_winsor["Product"].apply(extract_family)

    # Drop minggu terakhir pada df_pre_winsor (sinkron dengan df_family)
    last_week = df_pre_winsor["Week"].max()
    df_pre_winsor = df_pre_winsor[df_pre_winsor["Week"] != last_week]

    # Agregasi per week untuk family yang diminta (before winsorize)
    df_pre_agg = (
        df_pre_winsor[df_pre_winsor["Family"] == family]
        .groupby("Week", as_index=False)["Sales"]
        .sum()
    )

    # Data after winsorize (sudah dari df_family)
    df_post = df_family[df_family["Family"] == family].sort_values("Week")

    # Pastikan weeks sama (harusnya sama persis)
    weeks = df_post["Week"].values
    pre_sales = []
    for w in weeks:
        val = df_pre_agg[df_pre_agg["Week"] == w]["Sales"].values
        pre_sales.append(val[0] if len(val) > 0 else 0.0)

    series_before = pd.Series(pre_sales, dtype=float)
    series_after  = pd.Series(df_post["Sales"].values.astype(float))

    # ===== ADF Test (pada series after, seperti notebook) =====
    def _adf(s):
        s = pd.Series(s).dropna()
        if s.nunique() <= 1:
            return True, 0.0, 0.0
        try:
            r = adfuller(s)
            return r[1] < 0.05, float(r[1]), float(r[0])
        except Exception:
            return False, 1.0, 0.0

    is_stat, adf_p, adf_stat = _adf(series_after)

    # ===== Rolling Statistics (pada series after) =====
    rolling_mean = series_after.rolling(window=4, min_periods=1).mean()
    rolling_std  = series_after.rolling(window=4, min_periods=1).std().fillna(0)

    # ===== Boxplot stats (untuk visualisasi, seperti sebelumnya) =====
    def _boxplot_stats(s: pd.Series) -> dict:
        s = s.dropna()
        return {
            "min":    round(float(s.min()), 4),
            "q1":     round(float(s.quantile(0.25)), 4),
            "median": round(float(s.median()), 4),
            "q3":     round(float(s.quantile(0.75)), 4),
            "max":    round(float(s.max()), 4),
        }

    # ===== Tambahan untuk transparansi EDA =====
    max_lag = min(20, len(series_after) // 2)
    acf_before = _compute_acf(series_before, max_lag)
    acf_after = _compute_acf(series_after, max_lag)
    pacf_before = _compute_pacf(series_before, max_lag)
    pacf_after = _compute_pacf(series_after, max_lag)
    dist_before = _compute_histogram(series_before, bins=8)
    dist_after = _compute_histogram(series_after, bins=8)
    boxplot_before_summary = _boxplot_summary(series_before)
    boxplot_after_summary = _boxplot_summary(series_after)

    return {
        "family":        family,
        "count":         int(len(series_after)),
        "mean":          round(float(series_after.mean()), 4),
        "std":           round(float(series_after.std()), 4),
        "min":           round(float(series_after.min()), 4),
        "max":           round(float(series_after.max()), 4),
        "stationary":    bool(is_stat),
        "adf_statistic": round(float(adf_stat), 4),
        "adf_p_value":   round(float(adf_p), 4),
        "method":        "Linear Interpolation + IQR Winsorization (per SKU)",
        "weeks":         [d.strftime("%Y-%m-%d") for d in df_post["Date"]],
        "sales_before":  [round(float(v), 4) for v in series_before],
        "sales_after":   [round(float(v), 4) for v in series_after],
        "rolling_mean":  [round(float(v), 4) for v in rolling_mean],
        "rolling_std":   [round(float(v), 4) for v in rolling_std],
        "boxplot_before": _boxplot_stats(series_before),
        "boxplot_after":  _boxplot_stats(series_after),
        # Additional fields for transparency (used by frontend)
        "distribution_before": dist_before,
        "distribution_after": dist_after,
        "acf_before": acf_before,
        "acf_after": acf_after,
        "pacf_before": pacf_before,
        "pacf_after": pacf_after,
        "boxplot_before_summary": boxplot_before_summary,
        "boxplot_after_summary": boxplot_after_summary,
    }

def get_modelling(family: str, horizon: int = FORECAST_HORIZON) -> dict:
    """
    GET /modelling?family=...
    Cell 15 notebook — fit_arima(full_series), forecast + CI.
    CI: clip lower ke 0, upper > lower + 0.01.
    """
    series, dates = _get_family_series(family)

    if len(series) < 10:
        raise ValueError(f"Too few data points for family '{family}'.")

    # Cell 15 — fit on full series
    model              = fit_arima(series)
    forecast, conf_int = arima_forecast(model, horizon, with_ci=True)

    lower_ci_raw = conf_int[:, 0]
    upper_ci_raw = conf_int[:, 1]

    # Cell 15 — CI rules (verbatim)
    lower_ci = np.clip(lower_ci_raw, 0, None)
    upper_ci = np.maximum(upper_ci_raw, lower_ci + 0.01)
    upper_ci = np.maximum(upper_ci,    lower_ci + 0.01)  # notebook line 548

    last_date      = dates.iloc[-1]
    forecast_dates = [
        (last_date + pd.to_timedelta(i * 7, unit="D")).strftime("%Y-%m-%d")
        for i in range(1, horizon + 1)
    ]

    return {
        "family":           family,
        "order":            list(model.order),
        "aic":              round(float(model.aic()), 4) if model.aic() is not None else None,
        "horizon":          horizon,
        "forecast":         [round(float(v), 4) for v in forecast],
        "upper":            [round(float(v), 4) for v in upper_ci],
        "lower":            [round(float(v), 4) for v in lower_ci],
        "forecast_dates":   forecast_dates,
        "last_sales":       round(float(series[-1]), 4),
        "historical_weeks": [d.strftime("%Y-%m-%d") for d in dates],
        "historical_sales": [round(float(v), 4) for v in series],
        "historical_avg":   round(float(np.mean(series)), 4),
        "forecast_avg":     round(float(np.mean(forecast)), 4),
    }


def get_evaluation(family: str) -> dict:
    """
    GET /evaluation?family=...
    Cell 13 notebook — train/test split, clip, MAE/RMSE/sMAPE.
    np.clip(pred, 0, None) WAJIB ada sebelum hitung metrik (verbatim notebook).
    """
    series, dates = _get_family_series(family)

    n = len(series)
    if n <= TEST_SIZE:
        raise ValueError(f"Too few data points for family '{family}' (n={n}).")

    # Cell 13 — split (verbatim)
    train = series[:-TEST_SIZE]
    test  = series[-TEST_SIZE:]

    # Cell 13 — fit, forecast, CLIP, metrics (verbatim)
    model = fit_arima(train)
    pred  = arima_forecast(model, TEST_SIZE)
    pred  = np.clip(pred, 0, None)   # ← wajib, sesuai notebook cell 13 line 468

    metrics = evaluate_forecast(test, pred)

    dates_list  = dates.tolist()
    dates_train = [d.strftime("%Y-%m-%d") for d in dates_list[:-TEST_SIZE]]
    dates_test  = [d.strftime("%Y-%m-%d") for d in dates_list[-TEST_SIZE:]]

    return {
        "family":       family,
        "order":        list(model.order),
        "aic":          round(float(model.aic()), 4) if model.aic() is not None else None,
        "mae":          round(float(metrics["MAE"]),   4),
        "rmse":         round(float(metrics["RMSE"]),  4),
        "smape":        round(float(metrics["sMAPE"]), 4),
        "actual_train": [round(float(v), 4) for v in train],
        "actual_test":  [round(float(v), 4) for v in test],
        "fitted":       [round(float(v), 4) for v in pred],
        "dates_train":  dates_train,
        "dates_test":   dates_test,
    }
def get_data_cleaning_samples(family: str, limit: int = 5) -> dict:
    """
    Mengembalikan contoh data untuk transparansi cleaning:
    - missing before & after (sample)
    - outliers before & after (sample)
    - sales preview family (5 baris pertama)
    """
    pipe = _build_pipeline()
    df_full = pipe["df_full_long"]  # after winsorize, sudah drop last week
    df_pre_winsor = pipe["df_full_long_pre_winsor"].copy()
    df_before_interpol = pipe["df_full_long_before_interpol"]
    df_after_interpol = pipe["df_full_long_after_interpol"]

    # Assign family
    df_full["Family"] = df_full["Product"].apply(extract_family)
    df_pre_winsor["Family"] = df_pre_winsor["Product"].apply(extract_family)
    df_before_interpol["Family"] = df_before_interpol["Product"].apply(extract_family)
    df_after_interpol["Family"] = df_after_interpol["Product"].apply(extract_family)

    # ----- UNTUK MISSING VALUES: JANGAN DROP LAST WEEK (karena get_data_preparation menghitung termasuk minggu terakhir) -----
    # Filter family tanpa drop last week
    df_fam_before = df_before_interpol[df_before_interpol["Family"] == family]
    df_fam_after_interpol = df_after_interpol[df_after_interpol["Family"] == family]

    # Untuk outlier dan sales preview, kita tetap sinkron dengan df_family (sudah drop last week)
    # Drop last week untuk data pre_winsor dan full
    last_week = df_pre_winsor["Week"].max()
    df_pre_winsor = df_pre_winsor[df_pre_winsor["Week"] != last_week]
    df_fam_pre_winsor = df_pre_winsor[df_pre_winsor["Family"] == family]
    df_fam_after_winsor = df_full[df_full["Family"] == family]   # df_full sudah di-drop last week

    # SKU dalam family ini (gunakan dari pre_winsor yang sudah di-drop last week, agar sinkron)
    skus = df_fam_pre_winsor["Product"].unique()

    # ===== MISSING VALUES =====
    total_missing_before = 0
    missing_rows_list = []
    for sku in skus:
        mask = (df_fam_before["Product"] == sku)
        sub = df_fam_before.loc[mask]
        missing_mask = sub["Sales"].isna()
        missing_count = missing_mask.sum()
        total_missing_before += missing_count
        if missing_count > 0:
            missing_rows_list.append(sub[missing_mask])

    if missing_rows_list:
        missing_rows = pd.concat(missing_rows_list)
    else:
        missing_rows = pd.DataFrame(columns=["Product", "Week", "Sales"])

    missing_before_samples = missing_rows.head(limit)[["Product", "Week"]].to_dict(orient="records")
    for row in missing_before_samples:
        row["Sales"] = None

    missing_after_samples = []
    for row in missing_rows.head(limit).itertuples():
        matched = df_fam_after_interpol[
            (df_fam_after_interpol["Product"] == row.Product) &
            (df_fam_after_interpol["Week"] == row.Week)
        ]
        if not matched.empty:
            missing_after_samples.append({
                "Product": row.Product,
                "Week": row.Week,
                "Sales": matched.iloc[0]["Sales"]
            })
        else:
            missing_after_samples.append({"Product": row.Product, "Week": row.Week, "Sales": None})

    total_missing_after = 0

    # ===== OUTLIERS =====
    product_counts = pipe["product_outlier_counts_before"]
    total_outliers_before = sum(product_counts.get(p, 0) for p in skus)

    total_outliers_after = 0
    for product, grp in df_fam_after_winsor.groupby("Product"):
        s = grp["Sales"].dropna()
        if len(s) == 0:
            continue
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        total_outliers_after += int(((s < lower) | (s > upper)).sum())

    # Sample outliers before (dari df_fam_pre_winsor, yang sudah di-drop last week)
    outlier_rows = []
    for product in df_fam_pre_winsor["Product"].unique():
        s = df_fam_pre_winsor[df_fam_pre_winsor["Product"] == product]["Sales"].dropna()
        if len(s) < 2:
            continue
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = df_fam_pre_winsor[
            (df_fam_pre_winsor["Product"] == product) &
            ((df_fam_pre_winsor["Sales"] < lower) | (df_fam_pre_winsor["Sales"] > upper))
        ]
        if not outliers.empty:
            outlier_rows.append(outliers)

    if outlier_rows:
        df_outliers_before = pd.concat(outlier_rows)
        outliers_before_samples = df_outliers_before.head(limit)[["Product", "Week", "Sales"]].to_dict(orient="records")
    else:
        outliers_before_samples = []

    outliers_after_samples = []
    for row in df_outliers_before.head(limit).itertuples():
        matched = df_fam_after_winsor[
            (df_fam_after_winsor["Product"] == row.Product) &
            (df_fam_after_winsor["Week"] == row.Week)
        ]
        if not matched.empty:
            outliers_after_samples.append({
                "Product": row.Product,
                "Week": row.Week,
                "Sales": matched.iloc[0]["Sales"]
            })
        else:
            outliers_after_samples.append({"Product": row.Product, "Week": row.Week, "Sales": None})

    # ===== SALES PREVIEW FAMILY (5 minggu pertama, sudah drop last week) =====
    df_family = pipe["df_family"]
    df_fam_agg = df_family[df_family["Family"] == family].sort_values("Week").head(limit)

    # Hitung aggregate pre-winsor untuk family (tanpa last week)
    df_pre_agg = (
        df_pre_winsor[df_pre_winsor["Family"] == family]
        .groupby("Week", as_index=False)["Sales"]
        .sum()
    )
    sales_preview = []
    for _, row in df_fam_agg.iterrows():
        week_num = row["Week"]
        before_val = df_pre_agg[df_pre_agg["Week"] == week_num]["Sales"].values
        sales_preview.append({
            "week": row["Date"].strftime("%Y-%m-%d"),
            "sales_before": round(float(before_val[0]), 2) if len(before_val) > 0 else 0,
            "sales_after": round(float(row["Sales"]), 2)
        })

    return {
        "family": family,
        "missing_before_samples": missing_before_samples,
        "missing_after_samples": missing_after_samples,
        "total_missing_before": int(total_missing_before),
        "total_missing_after": total_missing_after,
        "outliers_before_samples": outliers_before_samples,
        "outliers_after_samples": outliers_after_samples,
        "total_outliers_before": total_outliers_before,
        "total_outliers_after": total_outliers_after,
        "sales_preview": sales_preview
    }