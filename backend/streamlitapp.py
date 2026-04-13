# streamlit_app_FIXED.py — Gap forecast diperbaiki, visualisasi kontinyu
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

st.set_page_config(page_title="ARIMA Stable Forecast GUI", layout="wide")
sns.set_style("whitegrid")

# ---- Config: change if your pipeline filename differs ----
PIPELINE_FILENAME = "arima_ta.py"  # or "arima_ta.py"
# ---------------------------------------------------------

# Try import pipeline module
try:
    import importlib.util, sys, pathlib
    spec = importlib.util.spec_from_file_location("pipeline_mod", pathlib.Path.cwd() / PIPELINE_FILENAME)
    pipeline = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = pipeline
    spec.loader.exec_module(pipeline)
except Exception as e:
    pipeline = None
    _err = str(e)

if pipeline is None:
    st.error(f"Tidak dapat menemukan atau mengimpor pipeline module '{PIPELINE_FILENAME}'. Error: {_err}")
    st.stop()

st.title("📈 ARIMA Stable Forecast — GUI")
st.write("Antarmuka: preprocessing → parameter (manual+auto) → training → forecast → trend classification.")

# ---------------- Sidebar ----------------
st.sidebar.header("Settings")
use_upload = st.sidebar.checkbox("Upload file Excel (override default)", value=False)
uploaded = None
if use_upload:
    uploaded = st.sidebar.file_uploader("Upload Excel (W1-W40).xlsx", type=["xlsx"])
forecast_horizon = st.sidebar.number_input("Forecast horizon (weeks)", min_value=1, max_value=26, value=5)
selected_product_btn = st.sidebar.button("Run selected product")
run_all_btn = st.sidebar.button("Run full pipeline (all products) — long")
show_acf_pacf = st.sidebar.checkbox("Show ACF/PACF (manual order)", value=True)
show_preproc_plots = st.sidebar.checkbox("Show exploratory plots (may be many)", value=False)

# ---------------- Load data ----------------
@st.cache_data
def load_default(path="AVG 12W & 5W (W1-W40).xlsx"):
    return pd.read_excel(path, header=None)

@st.cache_data
def load_uploaded(file):
    return pd.read_excel(file, header=None)

# load raw
if use_upload and uploaded:
    df_raw = load_uploaded(uploaded)
else:
    df_raw = load_default()

if df_raw is None:
    st.error("Gagal membaca dataset. Pastikan file berada di lokasi atau upload berhasil.")
    st.stop()

# find header row like pipeline
try:
    header_row = df_raw[df_raw.astype(str).apply(lambda x: x.str.contains("Kode Produk", case=False)).any(axis=1)].index[0]
    df = pd.read_excel(uploaded if (use_upload and uploaded) else "AVG 12W & 5W (W1-W40).xlsx", header=header_row)
    df = df.loc[:, ~df.columns.duplicated()]
except Exception as e:
    st.error(f"Header detection error: {e}")
    st.stop()

week_cols = [c for c in df.columns if isinstance(c, (int, float))]
if not week_cols:
    st.error("Kolom minggu (angka) tidak ditemukan. Pastikan format file W1-W40.")
    st.stop()

@st.cache_data
def melt_long(df):
    df_long = df.melt(id_vars=["PRINC 1", "Kode Produk", "Produk"], value_vars=week_cols, var_name="Week", value_name="Sales")
    start_date = pd.Timestamp("2024-01-01")
    df_long["Date"] = df_long["Week"].apply(lambda w: start_date + pd.to_timedelta((int(w) - 1) * 7, unit="D"))
    df_long = df_long.sort_values(["Produk", "Date"]).reset_index(drop=True)
    return df_long

df_long = melt_long(df)
products = df_long["Produk"].dropna().unique().tolist()
st.sidebar.markdown(f"**Products detected:** {len(products)}")
selected_product = st.sidebar.selectbox("Choose product", products)

# ---------- helper to build heatmap figure ----------
def get_heatmap_figure(df_long_local, product_name):
    df = df_long_local[df_long_local["Produk"] == product_name].copy()
    if df.empty:
        return None
    df["Month"] = df["Date"].dt.month
    df["WeekOfYear"] = df["Date"].dt.isocalendar().week.astype(int)
    pivot = df.pivot_table(index="Month", columns="WeekOfYear", values="Sales", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(pivot, cmap="YlOrRd", linewidths=.4, linecolor="gray", cbar_kws={'label': 'Avg Sales'}, ax=ax)
    ax.set_title(f"Seasonality Heatmap — {product_name}")
    ax.set_xlabel("Week of Year")
    ax.set_ylabel("Month")
    plt.tight_layout()
    return fig

# ---------- helper to format preprocessing summary ----------
def format_preproc_info(preproc_dict):
    if not preproc_dict:
        return "No preprocessing info."
    lines = []
    lines.append(f"• Product: **{preproc_dict.get('product','-')}**")
    lines.append(f"• Column used for modeling: **{preproc_dict.get('column_used','-')}** (d = {preproc_dict.get('d','-')})")
    pv = preproc_dict.get('p_value')
    if pv is not None:
        lines.append(f"• ADF p-value: **{pv:.4f}** → {'STATIONARY' if pv <= 0.05 else 'NOT STATIONARY'}")
    lines.append(f"• Mean (raw Sales): {preproc_dict.get('mean',np.nan):.3f}")
    lines.append(f"• Std (raw Sales): {preproc_dict.get('std',np.nan):.3f}")
    lines.append(f"• Outliers before cleaning: {preproc_dict.get('out_before',0)}")
    lines.append(f"• Outliers after cleaning: {preproc_dict.get('out_after',0)}")
    return "\n".join(lines)

# ---------- runner for single product ----------
def run_for_product(product_name, horizon=5, show_plots=False, show_acf=False):
    # prepare df_p and original_series BEFORE cleaning
    df_p_raw = df_long[df_long["Produk"] == product_name].copy().set_index("Date").sort_index()
    original_series = df_p_raw["Sales"].copy()

    # 1) cleaning + stationarity selection
    df_p = pipeline.clean_all_numeric(df_p_raw.copy())
    df_p, col_used, d = pipeline.make_stationary(df_p)

    # 2) preprocessing evaluation (human-friendly)
    preproc_info = pipeline.evaluate_product(df_p, original_series, col_used)

    # 3) manual order (from ACF/PACF) — safe lag handled inside pipeline.determine_manual_order
    try:
        p_manual, q_manual = pipeline.determine_manual_order(df_p[col_used])
    except Exception:
        p_manual, q_manual = None, None

    # 4) auto_arima
    arima_res = pipeline.fit_auto_arima_per_product(df_p, product_name, col_used)
    order_auto = arima_res["order"] if arima_res else None

    # 5) training eval (train_stable_model prints & returns eval metrics)
    eval_res = pipeline.train_stable_model(df_p, product_name, order_auto, col_used)

    # 6) full-series forecast for GUI (we will also compute notebook-style forecast from train/test for plotting)
    fc_full = pipeline.stable_forecast(df_p[col_used].dropna(), order=order_auto, steps=horizon)

    # Build ACF/PACF figures for GUI if requested
    acf_fig = pacf_fig = None
    if show_acf:
        try:
            series = df_p[col_used].dropna()
            n_obs = len(series)
            max_lag = min(20, max(1, n_obs // 2))
            fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
            plot_acf(series, lags=max_lag, ax=axes[0])
            plot_pacf(series, lags=max_lag, ax=axes[1], method='ywm')
            axes[0].set_title("ACF")
            axes[1].set_title("PACF")
            plt.tight_layout()
            acf_fig = fig
        except Exception:
            acf_fig = None

    return {
        "df_p_raw": df_p_raw,
        "df_p_clean": df_p,
        "original_series": original_series,
        "col_used": col_used,
        "d": d,
        "preproc_info": preproc_info,
        "p_manual": p_manual,
        "q_manual": q_manual,
        "arima_res": arima_res,
        "order_auto": order_auto,
        "eval_res": eval_res,
        "fc_full": fc_full,
        "acf_fig": acf_fig
    }

# ---------------- UI: run selected product ----------------
st.header("Product Analysis")

if selected_product_btn:
    with st.spinner(f"Running for {selected_product} ..."):
        out = run_for_product(selected_product, horizon=forecast_horizon, show_plots=show_preproc_plots, show_acf=show_acf_pacf)

    # Preprocessing box (human friendly)
    st.subheader("Preprocessing & Stationarity (human-friendly)")
    st.markdown(format_preproc_info(out["preproc_info"]))

    # If user wants exploratory plots, show the pipeline's visualize_product (but it may call plt.show in pipeline)
    if show_preproc_plots:
        st.subheader("Exploratory Plots (boxplot, trend, histogram...)")
        try:
            # pipeline.visualize_product usually calls plt.show; we call it (it will render)
            pipeline.visualize_product(out["df_p_clean"].copy(), selected_product)
            # If the pipeline function invoked plt.show, Streamlit may have captured the plot already.
        except Exception as e:
            st.warning(f"Could not show pipeline exploratory plots: {e}")

    # ACF/PACF & Manual order
    st.subheader("Penentuan Manual Order (ACF / PACF)")
    if out["acf_fig"] is not None:
        st.pyplot(out["acf_fig"])
    if out["p_manual"] is not None:
        st.markdown(f"• Manual chosen p = **{out['p_manual']}**, q = **{out['q_manual']}**, d = **{out['d']}**")
    else:
        st.markdown("• Manual order not available (series too short or error)")

    # Auto ARIMA result
    st.subheader("Auto ARIMA (grid / AIC)")
    if out["arima_res"]:
        p_auto, d_auto, q_auto = out["arima_res"]["order"]
        st.markdown(f"**Auto ARIMA selected:** ARIMA({p_auto},{d_auto},{q_auto})  —  AIC = {out['arima_res']['aic']:.3f}")
    else:
        st.markdown("Auto ARIMA failed to find a model.")

# =============== VISUALISASI 1: PREDIKSI PENUH (Sepanjang Data Aktual) ===============
    st.subheader(f"{selected_product} — Full Prediction vs Actual (dengan MSE)")

    series = out["df_p_clean"][out["col_used"]].dropna()
    order = out["order_auto"]
    n = len(series)

    if n < 3:
        st.warning("Data terlalu pendek untuk train/test split.")
    else:
        # 1) PREDIKSI ONE-STEP-AHEAD SEPANJANG DATA (seperti gambar kedua)
        # Kita akan prediksi setiap titik menggunakan data sebelumnya
        predictions = []
        for i in range(1, n):  # Mulai dari index 1 (butuh minimal 1 data sebelumnya)
            train_subset = series.iloc[:i]
            try:
                pred = pipeline.stable_forecast(train_subset, order=order, steps=1)
                predictions.append(pred.iloc[0])
            except:
                predictions.append(np.nan)
        
        # Buat series prediksi dengan index yang sesuai
        pred_series = pd.Series(predictions, index=series.index[1:])
        
        # 2) HITUNG MSE
        actual_for_mse = series.iloc[1:]  # Skip data pertama (tidak ada prediksi)
        mse = np.mean((actual_for_mse - pred_series.dropna()) ** 2)
        rmse = np.sqrt(mse)
        
        # 3) PLOT PREDIKSI PENUH
        fig1, ax1 = plt.subplots(figsize=(14, 5))
        
        # Plot Actual - Garis biru
        ax1.plot(series.index, series.values, 
                color='blue', linewidth=2, label='Actual Data', marker='o', markersize=3)
        
        # Plot Prediction - Garis merah
        ax1.plot(pred_series.index, pred_series.values,
                color='red', linewidth=2, label='Prediction (One-Step-Ahead)', 
                marker='s', markersize=3, alpha=0.8)
        
        # Styling
        ax1.set_title(f"{selected_product} — Prediction vs Actual | MSE: {mse:.2f} | RMSE: {rmse:.2f}", 
                     fontsize=14, fontweight='bold')
        ax1.set_xlabel("Date", fontsize=11)
        ax1.set_ylabel(out["col_used"], fontsize=11)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig1)
        
        # Tampilkan Metrics MSE
        col_mse1, col_mse2, col_mse3 = st.columns(3)
        with col_mse1:
            st.metric("MSE (Mean Squared Error)", f"{mse:.4f}")
        with col_mse2:
            st.metric("RMSE (Root MSE)", f"{rmse:.4f}")
        with col_mse3:
            mae = np.mean(np.abs(actual_for_mse - pred_series.dropna()))
            st.metric("MAE (Mean Absolute Error)", f"{mae:.4f}")

        st.markdown("---")

        # =============== VISUALISASI 2: FORECAST (Train/Test + Future) ===============
        st.subheader(f"{selected_product} — Forecast next {forecast_horizon} weeks (Continuous Timeline)")

        # 1) Train/test split (75/25)
        train_size = int(0.75 * n)
        train = series.iloc[:train_size]
        test = series.iloc[train_size:]

        # 2) Forecast untuk evaluasi (dari train, panjang = test)
        fc_test = pipeline.stable_forecast(train, order=order, steps=len(test))
        fc_test.index = test.index  # Align dengan timeline test

        # 3) Forecast future menggunakan FULL SERIES
        fc_future = pipeline.stable_forecast(series, order=order, steps=forecast_horizon)
        
        # Tentukan index untuk forecast future (melanjutkan dari data actual terakhir)
        if len(series) > 1:
            freq = series.index[1] - series.index[0]
        else:
            freq = pd.Timedelta(days=7)
        
        # Index dimulai TEPAT setelah data actual terakhir (no gap!)
        fc_future.index = pd.date_range(
            start=series.index[-1] + freq,
            periods=forecast_horizon,
            freq=freq
        )

        # 4) Plot dengan 3 komponen yang kontinyu
        fig2, ax2 = plt.subplots(figsize=(14, 5))

        # Plot Actual (Train + Test) - Garis biru solid
        ax2.plot(series.index, series.values, 
                color='#1f77b4', linewidth=2, label='Actual (Train + Test)', marker='o', markersize=4)

        # Plot Forecast dari Train (evaluasi) - Garis oranye dashed
        ax2.plot(fc_test.index, fc_test.values,
                color='#ff7f0e', linewidth=2.5, linestyle='--', 
                label='Forecast (from train)', marker='s', markersize=5)

        # Plot Forecast Future (prediksi) - Garis hijau dashed, KONTINYU dari actual
        ax2.plot(fc_future.index, fc_future.values,
                color='#2ca02c', linewidth=2.5, linestyle='--',
                label=f'Forecast next {forecast_horizon} weeks', marker='^', markersize=5)

        # Tambahkan titik koneksi antara actual terakhir dan forecast pertama
        ax2.plot([series.index[-1], fc_future.index[0]], 
                [series.values[-1], fc_future.values[0]],
                color='#2ca02c', linewidth=1.5, linestyle=':', alpha=0.7)

        # Marker vertikal untuk train/test split
        ax2.axvline(test.index[0], color='gray', linestyle=':', linewidth=1.5, 
                   label='Train/Test Split', alpha=0.7)

        # Styling
        ax2.set_title(f"{selected_product} — Forecast {forecast_horizon} Weeks", 
                     fontsize=14, fontweight='bold')
        ax2.set_xlabel("Date", fontsize=11)
        ax2.set_ylabel(out["col_used"], fontsize=11)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig2)

        # 5) Combine forecast untuk download
        # Gabungkan actual, forecast test, dan forecast future
        df_download = pd.DataFrame({
            'actual': series,
            'forecast_test': fc_test,
        })
        
        # Tambahkan forecast future sebagai kolom terpisah
        fc_future_aligned = pd.Series(index=df_download.index, dtype=float)
        df_download['forecast_future'] = fc_future_aligned
        
        # Tambahkan baris baru untuk forecast future
        for idx, val in fc_future.items():
            df_download.loc[idx, 'forecast_future'] = val

        st.download_button(
            "📥 Download Forecast Data (CSV)",
            data=df_download.to_csv(index=True),
            file_name=f"forecast_fixed_{selected_product}.csv",
            mime="text/csv"
        )

        # 6) Metrics summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Last Actual Value", f"{series.iloc[-1]:.3f}")
        with col2:
            st.metric("First Forecast Value", f"{fc_future.iloc[0]:.3f}")
        with col3:
            change = ((fc_future.iloc[0] - series.iloc[-1]) / series.iloc[-1] * 100)
            st.metric("Change (%)", f"{change:.2f}%")

        # Trend classification (human-friendly)
        st.subheader("Trend Classification (Fast / Medium / Slow)")
        trend = pipeline.classify_trend(out["df_p_clean"], fc_test if n >= 3 else out["fc_full"], window=5)
        if trend:
            st.markdown(f"- **Avg last 5 actual:** {trend['prev_avg']:.2f}\n\n- **Avg forecast test:** {trend['forecast_avg']:.2f}\n\n- **Change %:** {trend['change_pct']:.2f}%\n\n- **Category:** **{trend['category']}**")
            st.caption("Thresholds: >+15% → FAST, <-10% → SLOW, otherwise MEDIUM")
        else:
            st.warning("Tidak cukup data untuk klasifikasi tren.")

        # Seasonality heatmap
        st.subheader("Seasonality Heatmap")
        fig_hm = get_heatmap_figure(df_long, selected_product)
        if fig_hm:
            st.pyplot(fig_hm)
        else:
            st.warning("Tidak dapat membuat heatmap untuk produk ini.")

# ---------------- Run full pipeline (long) ----------------
if run_all_btn:
    confirm = st.sidebar.checkbox("Saya mengerti: jalankan full pipeline untuk semua produk (lama)", value=False)
    if not confirm:
        st.info("Centang checkbox konfirmasi di sidebar untuk melanjutkan.")
    else:
        st.info("Menjalankan full pipeline. Ini bisa memakan waktu lama.")
        progress_bar = st.progress(0)
        results = []
        for i, prod in enumerate(products):
            try:
                out_all = run_for_product(prod, horizon=forecast_horizon, show_plots=False, show_acf=False)
                # summarize minimal info per product
                eval_res = out_all["eval_res"]
                status = eval_res.get("status") if eval_res else "no-eval"
                results.append({
                    "product": prod,
                    "col_used": out_all["col_used"],
                    "order_auto": out_all["order_auto"],
                    "status": status
                })
            except Exception as e:
                results.append({"product": prod, "status": f"error: {e}"})
            progress_bar.progress(int((i+1)/len(products)*100))
        df_res = pd.DataFrame(results)
        st.success("Full pipeline selesai")
        st.dataframe(df_res)
        st.download_button("Download full results", data=df_res.to_csv(index=False), file_name="full_eval_results.csv")

st.markdown("---")
st.caption("Made for research purpose")