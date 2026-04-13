import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.arima.model import ARIMA
from scipy import stats
from pmdarima import auto_arima
from statsmodels.tsa.api import ExponentialSmoothing
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

"""# Pra-pemrosesan Data

## Product Visualize Function
"""

def visualize_product(df_product, product_name):
    """Visualisasi eksplorasi untuk setiap produk (diperbaiki supaya PACF & Q-Q tidak tertimpa)."""
    # Gunakan layout 4x2 supaya semua plot punya slot sendiri
    fig, axes = plt.subplots(4, 2, figsize=(14, 16))
    fig.suptitle(f"Exploratory Visualization - {product_name}", fontsize=14, fontweight="bold")

    # flatten axes for easier indexing
    ax = axes.flatten()

    # 1️⃣ Boxplot (All numeric columns) -> ax[0]
    try:
        num_cols = df_product.select_dtypes(include=[np.number]).columns.tolist()
        if len(num_cols) == 0:
            ax[0].text(0.5, 0.5, "No numeric columns", ha="center")
            ax[0].set_axis_off()
        else:
            sns.boxplot(data=df_product[num_cols], ax=ax[0])
            ax[0].set_title("Boxplot (All Numeric Columns)")
            ax[0].set_xticklabels(num_cols, rotation=45, ha="right")
    except Exception as e:
        ax[0].text(0.5, 0.5, f"Boxplot error: {e}", ha="center")
        ax[0].set_axis_off()

    # 2️⃣ Weekly Sales Trend -> ax[1]
    try:
        ax[1].plot(df_product.index, df_product["Sales"], color="orange", marker="o", linewidth=1)
        ax[1].set_title("Weekly Sales Trend")
        ax[1].set_xlabel("Date")
        ax[1].set_ylabel("Sales")
    except Exception as e:
        ax[1].text(0.5, 0.5, f"Trend error: {e}", ha="center")
        ax[1].set_axis_off()

    # 3️⃣ Sales Distribution (Histogram) -> ax[2]
    try:
        sns.histplot(df_product["Sales"].dropna(), bins=20, kde=True, ax=ax[2])
        ax[2].set_title("Sales Distribution (Histogram)")
    except Exception as e:
        ax[2].text(0.5, 0.5, f"Hist error: {e}", ha="center")
        ax[2].set_axis_off()

    # 4️⃣ Rolling Mean & Std -> ax[3]
    try:
        df_product["MA_4"] = df_product["Sales"].rolling(window=4, min_periods=1).mean()
        df_product["STD_4"] = df_product["Sales"].rolling(window=4, min_periods=1).std()
        ax[3].plot(df_product.index, df_product["Sales"], label="Original", alpha=0.6)
        ax[3].plot(df_product.index, df_product["MA_4"], label="4-Week MA", linewidth=2)
        ax[3].fill_between(
            df_product.index,
            df_product["MA_4"] - df_product["STD_4"],
            df_product["MA_4"] + df_product["STD_4"],
            alpha=0.1
        )
        ax[3].legend()
        ax[3].set_title("Rolling Mean & Std (4 weeks)")
    except Exception as e:
        ax[3].text(0.5, 0.5, f"Rolling error: {e}", ha="center")
        ax[3].set_axis_off()

    # 5️⃣ ACF Plot -> ax[4]
    try:
        n_obs = len(df_product["Sales"].dropna())
        max_lag = min(20, max(1, n_obs // 2))
        if n_obs > 1:
            plot_acf(df_product["Sales"].dropna(), ax=ax[4], lags=max_lag)
            ax[4].set_title(f"Autocorrelation (ACF) - Lags={max_lag}")
        else:
            ax[4].text(0.5, 0.5, "Data terlalu pendek untuk ACF", ha="center")
            ax[4].set_axis_off()
    except Exception as e:
        ax[4].text(0.5, 0.5, f"ACF error: {e}", ha="center")
        ax[4].set_axis_off()

    # 6️⃣ PACF Plot -> ax[5]
    try:
        if n_obs > 1:
            plot_pacf(df_product["Sales"].dropna(), ax=ax[5], lags=max_lag, method='ywm')
            ax[5].set_title(f"Partial Autocorrelation (PACF) - Lags={max_lag}")
        else:
            ax[5].text(0.5, 0.5, "Data terlalu pendek untuk PACF", ha="center")
            ax[5].set_axis_off()
    except Exception as e:
        ax[5].text(0.5, 0.5, f"PACF error: {e}", ha="center")
        ax[5].set_axis_off()

    # 7️⃣ Q-Q Plot -> ax[6]
    try:
        stats.probplot(df_product["Sales"].dropna(), dist="norm", plot=ax[6])
        ax[6].set_title("Q-Q Plot (Normality)")
    except Exception as e:
        ax[6].text(0.5, 0.5, f"Q-Q error: {e}", ha="center")
        ax[6].set_axis_off()

    # 8️⃣ Info / kosong -> ax[7]
    ax[7].axis('off')
    info_text = f"Count={len(df_product)}, Mean={df_product['Sales'].mean():.2f}, Std={df_product['Sales'].std():.2f}"
    ax[7].text(0.01, 0.5, info_text, va='center')

    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    plt.show()

"""## Cek Data Stasioner"""

def check_stationarity(series):
  series = series.dropna()
  if series.nunique() <= 1:
    return True, 0.0
  try:
    res = adfuller(series, autolag="AIC")
    return res[1] <= 0.05, res[1]
  except:
    return False, 1


def make_stationary(df_product):
  s = df_product["Sales"]
  is_stat, _ = check_stationarity(s)
  if is_stat:
    return df_product, "Sales", 0


  df_product["Sales_Diff"] = s.diff()
  if check_stationarity(df_product["Sales_Diff"].dropna())[0]:
    return df_product, "Sales_Diff", 1


  df_product["Sales_Diff2"] = df_product["Sales_Diff"].diff()
  return df_product, "Sales_Diff2", 2


# =============================================================
# CLEANING
# =============================================================


def clean_all_numeric(df_product):
  num_cols = df_product.select_dtypes(include=[np.number]).columns
  for col in num_cols:
      df_product[col] = df_product[col].interpolate(method='linear')
      Q1, Q3 = df_product[col].quantile([0.25, 0.75])
      IQR = Q3 - Q1
      df_product[col] = df_product[col].clip(Q1 - 1.5*IQR, Q3 + 1.5*IQR)
  return df_product

"""## Evaluasi Produk"""

def evaluate_product(df_product, original_series, col_used):
    # 1️⃣ Hitung stasioneritas pakai kolom stasioner
    try:
        p_value = adfuller(df_product[col_used].dropna(), autolag="AIC")[1]
        stationary = "Yes" if p_value <= 0.05 else "No"
    except:
        p_value = None
        stationary = "Error"

    # 2️⃣ Tentukan nilai d sesuai col_used
    if col_used == "Sales":
        d = 0
    elif col_used == "Sales_Diff":
        d = 1
    else:
        d = 2

    # 3️⃣ Statistik dasar
    mean_val = df_product["Sales"].mean()
    std_val = df_product["Sales"].std()

    # 4️⃣ Outliers sebelum cleaning
    Q1b, Q3b = original_series.quantile([0.25, 0.75])
    IQRb = Q3b - Q1b
    lowerb, upperb = Q1b - 1.5 * IQRb, Q3b + 1.5 * IQRb
    out_before = ((original_series < lowerb) | (original_series > upperb)).sum()

    # 5️⃣ Outliers setelah cleaning
    Q1a, Q3a = df_product["Sales"].quantile([0.25, 0.75])
    IQRa = Q3a - Q1a
    lowera, uppera = Q1a - 1.5 * IQRa, Q3a + 1.5 * IQRa
    out_after = ((df_product["Sales"] < lowera) | (df_product["Sales"] > uppera)).sum()

    # 6️⃣ Return hasil
    return {
        "product": df_product["Produk"].iloc[0],
        "mean": mean_val,
        "std": std_val,
        "out_before": out_before,
        "out_after": out_after,
        "stationary": stationary,
        "p_value": p_value,
        "column_used": col_used,
        "d": d
    }

def summarize_preprocessing(results):
    """Ringkasan hasil preprocessing"""
    total = len(results)
    stationary_count = sum(1 for r in results if r["stationary"] == "Yes")
    differencing_count = sum(1 for r in results if r["stationary"] == "No")
    constant_count = sum(1 for r in results if np.isclose(r["std"], 0))

    print("\n" + "=" * 52)
    print("PREPROCESSING SUMMARY:")
    print(f"• Total Produk: {total}")
    print(f"• Sudah Stasioner: {stationary_count}")
    print(f"• Perlu Differencing: {differencing_count}")
    print(f"• Data Konstan: {constant_count}")
    print("=" * 52)

"""# Penentuan Parameter Model"""

def plot_acf_pacf(series, product_name):
    """Plot ACF dan PACF untuk analisis parameter"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    plot_acf(series, lags=10, ax=axes[0])
    plot_pacf(series, lags=10, ax=axes[1])
    axes[0].set_title(f"ACF - {product_name}")
    axes[1].set_title(f"PACF - {product_name}")
    plt.tight_layout()
    plt.show()

def fit_auto_arima_per_product(df_product, product_name, col):
    series = df_product[col].dropna()
    try:
        model = auto_arima(
            series,
            start_p=0, start_q=0,
            max_p=3, max_q=3,
            max_d=2,
            seasonal=False,
            stepwise=True,
            suppress_warnings=True,
            error_action="ignore",
            maxiter=30
        )
        order = model.order
        print(f"✅ Auto ARIMA {product_name}: ARIMA{order} | AIC={model.aic():.2f}")
        return {"product": product_name, "order": order, "col": col, "aic": model.aic()}
    except Exception as e:
        print(f"❌ Auto ARIMA gagal untuk {product_name}: {e}")
        return None

def summarize_auto_arima(arima_results):
    """Ringkasan hasil Auto ARIMA"""
    valid_results = [r for r in arima_results if r and "aic" in r]
    if not valid_results:
        print("Tidak ada hasil Auto ARIMA yang valid.")
        return

    df_arima = pd.DataFrame(valid_results)
    df_arima = df_arima.sort_values("aic").head(10)

    print("=" * 52)
    print("AUTO ARIMA SUMMARY (Top 10 based on AIC)")
    print("=" * 52)
    print(df_arima.to_string(index=False))

"""## Training dan evaluasi model"""

def train_stable_model(df_product, product_name, order, col):
    series = df_product[col].dropna()
    n = len(series)

    if n < 10:
        print(f"⚠️ Data terlalu pendek untuk {product_name}")
        return None

    # Split train/test
    train_size = int(0.75 * n)
    train, test = series[:train_size], series[train_size:]

    # Forecast hanya dari TRAIN
    forecast = stable_forecast(train, order=order, steps=len(test))

    # 👉 Samakan index forecast dengan timeline test
    forecast.index = test.index

    # Metrics
    mae = mean_absolute_error(test, forecast)
    rmse = np.sqrt(mean_squared_error(test, forecast))
    mape = np.mean(np.abs((test - forecast) / (test + 1e-10))) * 100

    print(f"📊 {product_name} | RMSE={rmse:.3f}")

    # ==========================================================
    # 👉 PLOT ACTUAL (TRAIN + TEST) DAN FORECAST DALAM SATU GARIS
    # ==========================================================

    plt.figure(figsize=(12, 4))

    # 1) Actual data (Train + Test)
    plt.plot(series.index, series, label="Actual (Train + Test)", color="blue")

    # 2) Forecast yang langsung nyambung ke aktual
    plt.plot(forecast.index, forecast, label="Forecast", color="red", linestyle="--")

    # 3) Garis pemisah antara train & test (opsional)
    split_date = test.index[0]
    plt.axvline(split_date, color="gray", linestyle=":", label="Train/Test Split")

    plt.title(f"{product_name} | Train-Test + Forecast (Merged Timeline)")
    plt.xlabel("Date")
    plt.ylabel("Sales")
    plt.legend()
    plt.tight_layout()
    plt.show()

    return {
        "product": product_name,
        "order": order,
        "col": col,
        "mae": mae,
        "test_rmse": rmse,
        "mape": mape,
        "status": "STABLE"
    }

"""## Program Utama"""

def auto_tune_arima(df_product, product_name, col):
    series = df_product[col].dropna()
    try:
        model = auto_arima(
            series,
            start_p=0, start_q=0,
            max_p=3, max_q=3,
            max_d=2,
            seasonal=False,
            suppress_warnings=True,
            stepwise=True,
            error_action="ignore",
            maxiter=30
        )
        order = model.order
        print(f"♻️ Tuning {product_name}: ARIMA{order}")
        return {"product": product_name, "order": order, "col": col, "aic": model.aic()}
    except Exception:
        print(f"⚠️ Tuning gagal untuk {product_name}, fallback ETS")
        return {"product": product_name, "order": None, "col": col, "aic": None}

def stable_forecast(series, order=None, steps=5):
    """
    Forecast stabil untuk dataset pendek:
    1) Coba ARIMA
    2) Jika gagal → ETS
    3) Jika gagal → naive forecast
    """
    series = pd.Series(series).dropna()

    # Naive jika data sangat pendek
    if len(series) < 3:
        last = series.iloc[-1]
        return pd.Series([last] * steps)

    # 1️⃣ ARIMA terlebih dahulu
    if order is not None:
        try:
            model = ARIMA(series, order=order).fit()
            fc = model.forecast(steps=steps)
            return pd.Series(fc)
        except Exception as e:
            print(f"⚠️ ARIMA gagal: {e}")

    # 2️⃣ ETS fallback
    try:
        ets_model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal=None,
            damped=True
        ).fit()
        fc = ets_model.forecast(steps)
        return pd.Series(fc)
    except Exception as e:
        print(f"⚠️ ETS gagal: {e}")

    # 3️⃣ Naive fallback
    print("⚠️ Fallback ke naive forecast.")
    last = series.iloc[-1]
    return pd.Series([last] * steps)

def classify_trend(df_product, forecast_series, window=5):
    """
    Classify trend for a single product.
    - df_product: dataframe indexed by Date, must contain 'Sales' column.
    - forecast_series: pd.Series of forecast values (doesn't need datetime index, only need values).
    - window: number of past observations to average (default 5).
    Returns dict with prev_avg, forecast_avg, change_pct, category.
    """

    # Ensure series are numeric
    prev = df_product["Sales"].dropna().tail(window)
    if len(prev) == 0:
        return None

    prev_avg = float(prev.mean())
    forecast_avg = float(pd.Series(forecast_series).dropna().mean())

    # Avoid division by zero
    if prev_avg == 0:
        change_pct = np.nan
    else:
        change_pct = ((forecast_avg - prev_avg) / prev_avg) * 100.0

    # Thresholds:
    if pd.isna(change_pct):
        category = "UNKNOWN"
    elif change_pct > 15.0:
        category = "FAST-MOVING"
    elif change_pct < -10.0:
        category = "SLOW-MOVING"
    else:
        category = "MEDIUM-MOVING"

    return {
        "prev_avg": prev_avg,
        "forecast_avg": forecast_avg,
        "change_pct": change_pct,
        "category": category
    }

def classify_all_products(df_long, horizon=5, window=5, run_forecast_func=None, verbose=False):
    """
    Classify trend for all products.
    - df_long: long-format dataframe with columns ['Produk','Date','Sales', ...]
    - horizon: forecast horizon (weeks)
    - window: historical window to compute prev_avg
    - run_forecast_func: function that given (prod) returns (df_p_clean, col_used, arima_res, eval_res, fc)
                         If None, this function will use internal stable_forecast on df_p[col].
    Returns DataFrame with classification per product.
    """
    results = []
    products = df_long["Produk"].dropna().unique()
    total = len(products)

    for i, prod in enumerate(products, 1):
        try:
            df_p = df_long[df_long["Produk"] == prod].copy()
            df_p = df_p.set_index("Date").sort_index()

            # Clean & stationary to choose column
            df_p = clean_all_numeric(df_p)
            df_p, col_used, _ = make_stationary(df_p)

            # Obtain forecast series (prefer run_forecast_func if provided to reuse pipeline & ARIMA)
            if run_forecast_func is not None:
                # run_forecast_func must return (df_p_clean, col_used, arima_res, eval_res, fc)
                _, col_used2, arima_res, eval_res, fc = run_forecast_func(prod, show_plots=False, horizon=horizon)
                fc_vals = fc.values if hasattr(fc, "values") else list(fc)
            else:
                # fallback: use stable_forecast on the entire column
                series = df_p[col_used].dropna()
                fc_series = stable_forecast(series, order=None, steps=horizon)
                fc_vals = fc_series.values

            trend = classify_trend(df_p, pd.Series(fc_vals), window=window)
            if trend is None:
                row = {
                    "product": prod,
                    "col_used": col_used,
                    "order": None,
                    "prev_avg": np.nan,
                    "forecast_avg": np.nan,
                    "change_pct": np.nan,
                    "category": "NO_DATA"
                }
            else:
                row = {
                    "product": prod,
                    "col_used": col_used,
                    "order": arima_res.get("order") if (run_forecast_func is not None and arima_res is not None) else None,
                    "prev_avg": trend["prev_avg"],
                    "forecast_avg": trend["forecast_avg"],
                    "change_pct": trend["change_pct"],
                    "category": trend["category"]
                }

            results.append(row)
            if verbose and i % 50 == 0:
                print(f"[{i}/{total}] processed {prod} -> {row['category']}")

        except Exception as e:
            results.append({
                "product": prod,
                "col_used": None,
                "order": None,
                "prev_avg": np.nan,
                "forecast_avg": np.nan,
                "change_pct": np.nan,
                "category": f"ERROR: {e}"
            })
            if verbose:
                print(f"Error processing {prod}: {e}")
            continue

    df_res = pd.DataFrame(results)
    # normalize category strings
    df_res["category"] = df_res["category"].astype(str)
    return df_res

def plot_seasonality_heatmap(df_long, product_name):
    """Heatmap musiman (bulanan vs minggu ke-berapa) untuk 1 produk."""
    df = df_long[df_long["Produk"] == product_name].copy()

    if df.empty:
        print(f"⚠️ Produk '{product_name}' tidak ditemukan")
        return

    # Tambahkan kolom waktu
    df["Month"] = df["Date"].dt.month
    df["WeekOfYear"] = df["Date"].dt.isocalendar().week.astype(int)

    # Pivot: Month x Week → Avg Sales
    pivot = df.pivot_table(
        index="Month",
        columns="WeekOfYear",
        values="Sales",
        aggfunc="mean"
    )

    # Plot
    plt.figure(figsize=(16, 6))
    sns.heatmap(
        pivot,
        cmap="YlOrRd",
        linewidths=.5,
        linecolor="gray",
        cbar_kws={'label': 'Average Sales'}
    )
    plt.title(f"Seasonality Heatmap (Month vs Week) — {product_name}", fontsize=14)
    plt.xlabel("Week of Year")
    plt.ylabel("Month")
    plt.tight_layout()
    plt.show()

def main():
    print("=" * 80)
    print("AUTOMATIC PREPROCESSING + PENENTUAN & PELATIHAN MODEL (ARIMA)")
    print("=" * 80)

    # 1️⃣ LOAD DATASET
    df = pd.read_excel("AVG 12W & 5W (W1-W40).xlsx", header=None)
    header_row = df[df.astype(str).apply(lambda x: x.str.contains("Kode Produk", case=False)).any(axis=1)].index[0]
    df = pd.read_excel("AVG 12W & 5W (W1-W40).xlsx", header=header_row)
    df = df.loc[:, ~df.columns.duplicated()]

    week_cols = [c for c in df.columns if isinstance(c, (int, float))]

    df_long = df.melt(
        id_vars=["PRINC 1", "Kode Produk", "Produk"],
        value_vars=week_cols,
        var_name="Week",
        value_name="Sales"
    )

    # Buat kolom tanggal
    start_date = pd.Timestamp("2024-01-01")
    df_long["Date"] = df_long["Week"].apply(lambda x: start_date + pd.to_timedelta((int(x) - 1)*7, unit="D"))
    df_long = df_long.sort_values(["Produk", "Date"])

    # Daftar semua produk
    products = df_long["Produk"].dropna().unique()
    print(f"🔍 Menjalankan untuk SEMUA {len(products)} produk.\n")

    # Penyimpanan hasil
    preprocessing_results = []
    arima_results = []
    evaluation_results = []

    # ============================================================
    # A. PREPROCESSING + AUTO ARIMA
    # ============================================================
    for prod in products:
        df_product = df_long[df_long["Produk"] == prod].copy()
        df_product = df_product.set_index("Date").sort_index()
        original_series = df_product["Sales"].copy()

        # 1️⃣ Cleaning dan differencing
        df_product = clean_all_numeric(df_product)
        df_product, col_used, d = make_stationary(df_product)

        # Simpan hasil preprocessing
        result = evaluate_product(df_product, original_series, col_used)
        preprocessing_results.append(result)

        # di dalam loop preprocess
        print(f"\n📊 Visualisasi eksploratif untuk produk: {prod}")
        visualize_product(df_product, prod)

        # 🔥 Tambahan: Seasonality Heatmap
        plot_seasonality_heatmap(df_long, prod)


        # 2️⃣ AUTO ARIMA
        arima_result = fit_auto_arima_per_product(df_product, prod, col_used)
        if arima_result is not None:
            arima_results.append(arima_result)

    # ============================================================
    # B. TRAINING MENGGUNAKAN stable_forecast()
    # ============================================================
    print("\n" + "=" * 70)
    print("TAHAP: PELATIHAN & EVALUASI MODEL (STABLE FORECAST)")
    print("=" * 70)

    valid_models = [m for m in arima_results if m is not None]

    for model_row in valid_models:

        prod = model_row["product"]
        order = model_row["order"]
        col = model_row["col"]

        df_product = df_long[df_long["Produk"] == prod].set_index("Date").copy()
        df_product = clean_all_numeric(df_product)
        df_product, col_use, d = make_stationary(df_product)

        try:
            eval_result = train_stable_model(df_product, prod, order, col_use)
            if eval_result:
                evaluation_results.append(eval_result)
        except Exception as e:
            print(f"❌ Error training {prod}: {e}")
            continue

    # ============================================================
    # C. DATAFRAME HASIL EVALUASI
    # ============================================================
    df_eval = pd.DataFrame(evaluation_results)

    print("\n📊 RINGKASAN HASIL EVALUASI (Top 10 RMSE TERENDAH)")
    if not df_eval.empty:
        print(df_eval.sort_values("test_rmse").head(10).to_string(index=False))
    else:
        print("❌ Tidak ada hasil evaluasi model yang valid.")

    print("\n✅ Semua produk selesai diproses.\n")

    return df_long, df_eval


# ======================================================================
# AUTO TUNING (C.1)
# ======================================================================
# ======================================================================
# AUTO TUNING (C.1)
# ======================================================================
if __name__ == "__main__":
    RUN_CLASSIFICATION = True
    CLASS_HORIZON = 5
    CLASS_WINDOW = 5

    df_long, df_eval = main()

    print("\n" + "=" * 70)
    print("TAHAP C.1: AUTO-TUNING MODEL UNTUK PRODUK UNDERFIT / OVERFIT")
    print("=" * 70)

    tuned_results = []

    if not df_eval.empty:
        for row in df_eval.itertuples():
            if row.status in ("OVERFIT", "UNDERFIT"):
                print(f"\n🔄 Tuning model untuk {row.product} ...")

                df_product = df_long[df_long["Produk"] == row.product].set_index("Date").copy()
                df_product = clean_all_numeric(df_product)
                df_product, col_used, _ = make_stationary(df_product)

                col_for_tune = getattr(row, "col", None) or col_used

                tuned_model = auto_tune_arima(df_product, row.product, col_for_tune)
                if tuned_model:
                    tuned_results.append(tuned_model)
    else:
        print("❌ Tidak ada data evaluasi model.")

    if tuned_results:
        df_tuned = pd.DataFrame(tuned_results)
        print("\n📊 HASIL TUNING MODEL (TOP 10 AIC TERENDAH)")
        print(df_tuned.sort_values("aic").head(10).to_string(index=False))
    else:
        print("✅ Semua model BALANCED, tidak perlu tuning tambahan.")

    # ======================================================================
    # E. KLASIFIKASI TREN PRODUK
    # ======================================================================
    if RUN_CLASSIFICATION:
        print("\n" + "="*70)
        print("TAHAP E: KLASIFIKASI TREN PRODUK (FAST / MEDIUM / SLOW)")
        print("="*70)

        df_class = classify_all_products(
            df_long,
            horizon=CLASS_HORIZON,
            window=CLASS_WINDOW,
            run_forecast_func=None,
            verbose=False
        )

        fast = df_class[df_class["category"] == "FAST-MOVING"]["product"].tolist()
        med  = df_class[df_class["category"] == "MEDIUM-MOVING"]["product"].tolist()
        slow = df_class[df_class["category"] == "SLOW-MOVING"]["product"].tolist()

        print("\n📌 FAST-MOVING PRODUCTS:")
        if not fast:
            print("  (Tidak ada)")
        else:
            for p in fast:
                print(" -", p)

        print("\n📌 MEDIUM-MOVING PRODUCTS:")
        if not med:
            print("  (Tidak ada)")
        else:
            for p in med:
                print(" -", p)

        print("\n📌 SLOW-MOVING PRODUCTS:")
        if not slow:
            print("  (Tidak ada)")
        else:
            for p in slow:
                print(" -", p)