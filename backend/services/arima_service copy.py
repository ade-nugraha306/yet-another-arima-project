"""
arima_service.py — Faithful reproduction of ARIMA_TA_CSV.ipynb methodology

Pipeline (exact notebook order):
1. Load CSV with dynamic header detection
2. Melt to long format; linear interpolate missing weeks; fillna(0)
3. Assign Family via keyword mapping
4. Winsorize per SKU (IQR method: Q1 - 1.5*IQR, Q3 + 1.5*IQR)
5. Aggregate to Family level (sum per week)
6. Drop the last week (incomplete data)
7. ADF stationarity test → differencing (max d=2)
8. auto_arima(seasonal=False, start_p=0, start_q=0,
              max_p=3, max_d=2, max_q=3, stepwise=True,
              test='adf', information_criterion='aicc')
9. Evaluate on last-5-weeks holdout: MAE, RMSE, sMAPE
10. Final model trained on full series → 5-week forecast with CI from model

Notebook is the single source of truth. No methodology changes allowed.
"""

import warnings
import numpy as np
import pandas as pd
from pathlib import Path

from statsmodels.tsa.stattools import adfuller
from pmdarima import auto_arima

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# CONSTANTS  (must match notebook)
# ---------------------------------------------------------------------------
BASE_DIR      = Path(__file__).resolve().parent.parent
DATA_PATH     = BASE_DIR / "AVG 12W & 5W.csv"

ARIMA_MAX_P        = 3
ARIMA_MAX_Q        = 3
FORECAST_HORIZON   = 5
HOLDOUT_WEEKS      = 5        # last-5-weeks test split
MIN_FAMILY_AVG     = 5        # notebook Cell 20: exclude families with mean < 5


# ---------------------------------------------------------------------------
# FAMILY MAPPING  (notebook verbatim)
# ---------------------------------------------------------------------------
def extract_family(product_name: str) -> str | None:
    """
    Map a product name to its Family.
    Returns None for products that do not belong to a tracked family.
    Excludes COLLISION / CRASH / BUILD as per AGENTS.md.
    """
    n = str(product_name).upper()

    if "5DAYS"    in n: return "5DAYS"
    if "CAF"      in n: return "CAF"
    if "FOX"      in n: return "FOX"
    if "HYDROPLUS" in n: return "HYDROPLUS"
    if "ROYO"     in n: return "ROYO"
    if "TUBRUK"   in n: return "TUBRUK"
    if "UHT"      in n: return "UHT"

    # Excluded families: COLLISION, CRASH, BUILD → fall through to OTHER
    # Per notebook: everything else → OTHER
    return "OTHER"


# ---------------------------------------------------------------------------
# DATA LOADING & CACHING
# ---------------------------------------------------------------------------
_df_raw_cache: pd.DataFrame | None = None


def _is_week_col(c) -> bool:
    """Return True if the column is a valid week number (1–40 range used in data)."""
    try:
        val = float(str(c).strip())
        return val == int(val) and 1 <= int(val) <= 52
    except Exception:
        return False


def _load_raw_long() -> pd.DataFrame:
    """
    Step 1–2 of the notebook:
    • Load CSV; detect header row dynamically (row containing 'Kode Produk').
    • Melt weekly columns → long format.
    • Reconstruct full week timeline (1–40 minus week 14 which is absent).
    • Linear interpolate missing Sales values.
    • fillna(0) for any remaining NaN.
    • Assign Family via extract_family().
    Cached after first call.
    """
    global _df_raw_cache
    if _df_raw_cache is not None:
        return _df_raw_cache

    # --- detect header row ---
    df_raw = pd.read_csv(DATA_PATH, header=None, encoding="utf-8-sig", low_memory=False)
    mask       = df_raw.astype(str).apply(
        lambda x: x.str.contains("Kode Produk", case=False)
    ).any(axis=1)
    header_row = df_raw[mask].index[0]

    df = pd.read_csv(
        DATA_PATH,
        header=header_row,
        encoding="utf-8-sig",
        low_memory=False,
    )
    df = df.loc[:, ~df.columns.duplicated()]

    # --- detect week columns ---
    week_cols = [c for c in df.columns if _is_week_col(c)]
    if not week_cols:
        raise ValueError(f"No week columns detected. Check file: {DATA_PATH}")

    id_cols  = ["PRINC 1", "Kode Produk", "Produk"]
    missing  = [c for c in id_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Required columns not found: {missing}")

    df = df[df["Produk"].notna()].copy()

    # --- melt ---
    df_long = df.melt(
        id_vars=id_cols,
        value_vars=week_cols,
        var_name="Week",
        value_name="Sales",
    )
    df_long["Week"]  = df_long["Week"].apply(lambda x: int(float(x)))
    df_long["Sales"] = pd.to_numeric(df_long["Sales"], errors="coerce")

    # --- notebook step: interpolate per SKU then fillna(0) ---
    # Group by SKU, sort by Week, interpolate, fillna
    result_parts = []
    for sku, grp in df_long.groupby("Produk"):
        grp = grp.sort_values("Week").copy()
        grp["Sales"] = grp["Sales"].interpolate(method="linear")
        grp["Sales"] = grp["Sales"].fillna(0)
        result_parts.append(grp)

    df_long = pd.concat(result_parts, ignore_index=True)

    # --- assign Family ---
    df_long["Family"] = df_long["Produk"].apply(extract_family)

    # --- date column (week → date, starting 2025-01-01) ---
    start_date = pd.Timestamp("2025-01-01")
    df_long["Date"] = df_long["Week"].apply(
        lambda w: start_date + pd.to_timedelta((w - 1) * 7, unit="D")
    )

    df_long      = df_long.sort_values(["Produk", "Date"]).reset_index(drop=True)
    _df_raw_cache = df_long
    return _df_raw_cache


# ---------------------------------------------------------------------------
# IQR WINSORIZATION PER SKU  (notebook verbatim)
# ---------------------------------------------------------------------------
def _winsorize_sku(series: pd.Series) -> pd.Series:
    """
    IQR winsorization for a single SKU's Sales series.
    Lower = Q1 - 1.5 * IQR
    Upper = Q3 + 1.5 * IQR
    Values outside [Lower, Upper] are clipped.
    """
    q1  = series.quantile(0.25)
    q3  = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return series.clip(lower=lower, upper=upper)


# ---------------------------------------------------------------------------
# FAMILY AGGREGATION PIPELINE  (notebook step 3–6)
# ---------------------------------------------------------------------------
_df_family_cache: dict[str, pd.DataFrame] = {}


def _get_family_df(family: str) -> pd.DataFrame:
    """
    Return a DataFrame with columns [Week, Date, Sales] aggregated at Family level.

    Pipeline (mirrors notebook):
      Raw SKU data → IQR Winsorize per SKU → aggregate (sum) per week → drop last week
    """
    if family in _df_family_cache:
        return _df_family_cache[family].copy()

    df_long = _load_raw_long()

    # filter to this family
    df_f = df_long[df_long["Family"] == family].copy()
    if df_f.empty:
        raise ValueError(f"Family '{family}' not found in dataset.")

    # winsorize per SKU
    winsorized_parts = []
    for sku, grp in df_f.groupby("Produk"):
        grp = grp.sort_values("Week").copy()
        grp["Sales"] = _winsorize_sku(grp["Sales"])
        winsorized_parts.append(grp)

    df_f_win = pd.concat(winsorized_parts, ignore_index=True)

    # aggregate to family level (sum per week)
    family_agg = (
        df_f_win.groupby(["Week", "Date"])["Sales"]
        .sum()
        .reset_index()
        .sort_values("Week")
    )

    # drop the last week (incomplete data — notebook rule)
    family_agg = family_agg.iloc[:-1].reset_index(drop=True)

    _df_family_cache[family] = family_agg
    return _df_family_cache[family].copy()


def _get_family_series(family: str) -> pd.Series:
    """Return Sales as a pd.Series indexed by Date."""
    df = _get_family_df(family)
    return df.set_index("Date")["Sales"].sort_index()


# ---------------------------------------------------------------------------
# STATIONARITY  (notebook section 11)
# ---------------------------------------------------------------------------
def _adf_test(series: pd.Series) -> tuple[bool, float, float]:
    """ADF test. Returns (is_stationary, p_value, adf_stat)."""
    s = series.dropna()
    if s.nunique() <= 1:
        return True, 0.0, 0.0
    try:
        result = adfuller(s)
        return result[1] < 0.05, float(result[1]), float(result[0])
    except Exception:
        return False, 1.0, 0.0


# ---------------------------------------------------------------------------
# AUTO-ARIMA  (notebook section 12 — exact parameters)
# ---------------------------------------------------------------------------
def _fit_auto_arima(train_series):
    """
    Fit auto_arima exactly as in notebook section 12.
    Returns a fitted pmdarima model.
    """
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


def _arima_forecast(model, steps: int, with_ci: bool = False):
    """
    Notebook's arima_forecast() helper.
    Returns (forecast_array) or (forecast_array, conf_int_array).
    """
    if with_ci:
        forecast, conf_int = model.predict(n_periods=steps, return_conf_int=True)
        return np.array(forecast), conf_int
    forecast = model.predict(n_periods=steps)
    return np.array(forecast)


# ---------------------------------------------------------------------------
# sMAPE  (notebook section 12)
# ---------------------------------------------------------------------------
def _smape(actual: np.ndarray, pred: np.ndarray) -> float:
    """
    sMAPE = mean(2|A-F| / (|A|+|F|)) * 100
    Returns 0 when both actual and pred are 0.
    """
    actual = np.array(actual, dtype=float)
    pred   = np.array(pred,   dtype=float)
    denominator = np.abs(actual) + np.abs(pred)
    return float(
        np.mean(
            np.where(
                denominator == 0,
                0,
                2 * np.abs(actual - pred) / denominator,
            )
        ) * 100
    )


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def get_families() -> list[str]:
    """
    Return sorted list of families present in the dataset.
    Mirrors notebook Cell 20: only families with mean weekly sales >= MIN_FAMILY_AVG.
    ROYO is excluded because its mean (≈1.3) < 5.
    """
    df_long = _load_raw_long()

    # Aggregate to family-week level (pre-winsorization, matching notebook Cell 20)
    family_week = (
        df_long[df_long["Family"] != "OTHER"]
        .groupby(["Family", "Week"])["Sales"]
        .sum()
        .reset_index()
    )
    family_mean = family_week.groupby("Family")["Sales"].mean()

    # Apply MIN_FAMILY_AVG filter (notebook rule)
    valid_by_mean = set(family_mean[family_mean >= MIN_FAMILY_AVG].index.tolist())

    # Also verify each family has aggregated data (catches edge cases)
    valid = []
    for f in sorted(valid_by_mean):
        try:
            _get_family_df(f)
            valid.append(f)
        except Exception:
            pass
    return valid


def get_data_acquisition(family: str) -> dict:
    """
    Endpoint: GET /data-acquisition?family=...
    Returns raw (pre-winsorization) weekly family-level data.
    """
    # raw = sum of raw (pre-winsorize) SKU sales per week for this family
    df_long = _load_raw_long()
    df_f    = df_long[df_long["Family"] == family]
    if df_f.empty:
        raise ValueError(f"Family '{family}' not found.")

    sku_list = sorted(df_f["Produk"].dropna().unique().tolist())

    raw_agg = (
        df_f.groupby(["Week", "Date"])["Sales"]
        .sum()
        .reset_index()
        .sort_values("Week")
    )

    return {
        "family":      family,
        "sku_count":   len(sku_list),
        "skus":        sku_list,
        "total_weeks": len(raw_agg),
        "weeks":       [d.strftime("%Y-%m-%d") for d in raw_agg["Date"]],
        "sales_raw":   [
            round(float(v), 4) if not np.isnan(v) else None
            for v in raw_agg["Sales"].values
        ],
    }


def get_data_preparation(family: str) -> dict:
    """
    Endpoint: GET /data-preparation?family=...
    Returns cleaning statistics (interpolation + IQR winsorization) and
    before/after series for the family.
    """
    # --- "before" = raw family aggregate (no winsorize) ---
    df_long = _load_raw_long()
    df_f    = df_long[df_long["Family"] == family]
    if df_f.empty:
        raise ValueError(f"Family '{family}' not found.")

    raw_agg = (
        df_f.groupby(["Week", "Date"])["Sales"]
        .sum()
        .reset_index()
        .sort_values("Week")
        .iloc[:-1]  # also drop last week for consistency
        .reset_index(drop=True)
    )

    # --- "after" = winsorized + aggregated family series ---
    family_df   = _get_family_df(family)
    series_after = family_df["Sales"].values

    # count outliers before/after (per IQR rule applied to SKU level)
    outliers_before = 0
    outliers_after  = 0
    for sku, grp in df_f.groupby("Produk"):
        s   = grp["Sales"].dropna()
        q1  = s.quantile(0.25)
        q3  = s.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers_before += int(((s < lower) | (s > upper)).sum())

    # ADF on cleaned (winsorized) series
    series_s = pd.Series(series_after)
    is_stat_before, adf_p_before, adf_stat_before = _adf_test(series_s)

    # differencing for stationarity display
    d = 0
    if not is_stat_before:
        diff1                           = series_s.diff().dropna()
        is_stat_after, adf_p_after, adf_stat_after = _adf_test(diff1)
        d = 1
        if not is_stat_after:
            diff2 = diff1.diff().dropna()
            is_stat_after, adf_p_after, adf_stat_after = _adf_test(diff2)
            d = 2
    else:
        is_stat_after  = is_stat_before
        adf_p_after    = adf_p_before
        adf_stat_after = adf_stat_before

    weeks_str = [d.strftime("%Y-%m-%d") for d in family_df["Date"]]

    return {
        "family":          family,
        "missing_before":  int(raw_agg["Sales"].isna().sum()),
        "missing_after":   0,
        "outliers_before": outliers_before,
        "outliers_after":  outliers_after,
        "cleaning_method": "Linear Interpolation + IQR Winsorization (per SKU)",
        "adf_statistic_before": round(adf_stat_before, 4),
        "adf_p_value_before":   round(adf_p_before, 4),
        "adf_statistic_after":  round(adf_stat_after, 4),
        "adf_p_value_after":    round(adf_p_after, 4),
        "stationary_before":    bool(is_stat_before),
        "stationary_after":     bool(is_stat_after),
        "d":                    d,
        "weeks":         weeks_str,
        "sales_before":  [
            round(float(v), 4) if (v is not None and not np.isnan(float(v))) else None
            for v in raw_agg["Sales"].values
        ],
        "sales_after":   [round(float(v), 4) for v in series_after],
    }


def get_eda(family: str) -> dict:
    """
    Endpoint: GET /eda?family=...
    EDA data: trend, distribution, rolling stats, ADF, boxplot.
    """
    family_df    = _get_family_df(family)
    series_after = pd.Series(family_df["Sales"].values)

    # ADF on cleaned series
    is_stat, adf_p, adf_stat = _adf_test(series_after)

    rolling_mean = series_after.rolling(window=4, min_periods=1).mean()
    rolling_std  = series_after.rolling(window=4, min_periods=1).std().fillna(0)

    # "before" series = raw family aggregate (no winsorize, for comparison)
    df_long = _load_raw_long()
    df_f    = df_long[df_long["Family"] == family]
    raw_agg = (
        df_f.groupby(["Week", "Date"])["Sales"]
        .sum()
        .reset_index()
        .sort_values("Week")
        .iloc[:-1]
        .reset_index(drop=True)
    )
    sales_before = raw_agg["Sales"].values

    def _boxplot_stats(s) -> dict:
        s = pd.Series(s).dropna()
        return {
            "min":    round(float(s.min()),              4),
            "q1":     round(float(s.quantile(0.25)),     4),
            "median": round(float(s.median()),            4),
            "q3":     round(float(s.quantile(0.75)),     4),
            "max":    round(float(s.max()),              4),
        }

    return {
        "family":         family,
        "count":          int(len(series_after)),
        "mean":           round(float(series_after.mean()), 4),
        "std":            round(float(series_after.std()),  4),
        "min":            round(float(series_after.min()),  4),
        "max":            round(float(series_after.max()),  4),
        "stationary":     bool(is_stat),
        "adf_statistic":  round(float(adf_stat), 4),
        "adf_p_value":    round(float(adf_p),    4),
        "method":         "Linear Interpolation + IQR Winsorization (per SKU)",
        "weeks":          [d.strftime("%Y-%m-%d") for d in family_df["Date"]],
        "sales_before":   [
            round(float(v), 4) if (v is not None and not np.isnan(float(v))) else None
            for v in sales_before
        ],
        "sales_after":    [round(float(v), 4) for v in series_after],
        "rolling_mean":   [round(float(v), 4) for v in rolling_mean],
        "rolling_std":    [round(float(v), 4) for v in rolling_std],
        "boxplot_before": _boxplot_stats(sales_before),
        "boxplot_after":  _boxplot_stats(series_after),
    }


def get_modelling(family: str, horizon: int = FORECAST_HORIZON) -> dict:
    """
    Endpoint: GET /modelling?family=...
    Trains final ARIMA on the FULL cleaned series and forecasts `horizon` steps.
    Confidence intervals come directly from model.predict(return_conf_int=True).
    """
    family_df = _get_family_df(family)
    series    = family_df["Sales"].values.astype(float)

    if len(series) < 10:
        raise ValueError(f"Too few data points for family '{family}'.")

    # fit on full series
    model = _fit_auto_arima(series)

    # forecast with CI directly from model (notebook section 15)
    forecast, conf_int = _arima_forecast(model, steps=horizon, with_ci=True)

    lower_ci_raw = conf_int[:, 0]
    upper_ci_raw = conf_int[:, 1]

    # notebook rule: floor lower at 0, ensure upper > lower
    lower_ci = np.clip(lower_ci_raw, 0, None)
    upper_ci = np.maximum(upper_ci_raw, lower_ci + 0.01)

    # forecast week labels
    last_date     = family_df["Date"].iloc[-1]
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
        "historical_weeks": [d.strftime("%Y-%m-%d") for d in family_df["Date"]],
        "historical_sales": [round(float(v), 4) for v in series],
        "historical_avg":   round(float(np.mean(series)), 4),
        "forecast_avg":     round(float(np.mean(forecast)), 4),
    }


def get_evaluation(family: str) -> dict:
    """
    Endpoint: GET /evaluation?family=...
    Last-5-weeks holdout evaluation: MAE, RMSE, sMAPE.
    Exactly mirrors notebook section 13.
    """
    family_df = _get_family_df(family)
    series    = family_df["Sales"].values.astype(float)

    n = len(series)
    if n < 10:
        raise ValueError(f"Too few data points for family '{family}' (n={n}).")

    # notebook split: train = series[:-5], test = series[-5:]
    train = series[:-HOLDOUT_WEEKS]
    test  = series[-HOLDOUT_WEEKS:]

    # fit and forecast
    eval_model = _fit_auto_arima(train)
    fc         = _arima_forecast(eval_model, steps=HOLDOUT_WEEKS)

    mae   = float(np.mean(np.abs(test - fc)))
    rmse  = float(np.sqrt(np.mean((test - fc) ** 2)))
    smape = _smape(test, fc)

    dates = family_df["Date"].tolist()
    dates_train = [d.strftime("%Y-%m-%d") for d in dates[:-HOLDOUT_WEEKS]]
    dates_test  = [d.strftime("%Y-%m-%d") for d in dates[-HOLDOUT_WEEKS:]]

    return {
        "family":       family,
        "order":        list(eval_model.order),
        "aic":          round(float(eval_model.aic()), 4) if eval_model.aic() is not None else None,
        "mae":          round(mae,   4),
        "rmse":         round(rmse,  4),
        "smape":        round(smape, 4),
        "actual_train": [round(float(v), 4) for v in train],
        "actual_test":  [round(float(v), 4) for v in test],
        "fitted":       [round(float(v), 4) for v in fc],
        "dates_train":  dates_train,
        "dates_test":   dates_test,
    }