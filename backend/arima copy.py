# ============================================================================
# GUI PREPROCESSING DATA UNTUK ARIMA - MULTI PRODUCT VERSION (Tkinter)
# PT. GONUSA PRIMA DISTRIBUSI
# Author: Ade Nugraha (236152008)
# ============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf
from scipy import stats
import warnings
import os
import tkinter as tk
from tkinter import ttk, messagebox

warnings.filterwarnings("ignore")

plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")

# ============================================================================
# VISUALISASI PER PRODUK
# ============================================================================


def visualize_product(df_product, product_name):
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle(
        f"Exploratory Visualization - {product_name}", fontsize=14, fontweight="bold"
    )

    # 1️⃣ Boxplot
    num_cols = df_product.select_dtypes(include=[np.number]).columns.tolist()
    sns.boxplot(data=df_product[num_cols], ax=axes[0, 0])
    axes[0, 0].set_title("Boxplot (All Numeric Columns)")
    axes[0, 0].set_xticklabels(num_cols, rotation=45, ha="right")

    # 2️⃣ Weekly Sales
    axes[0, 1].plot(
        df_product.index, df_product["Sales"], color="orange", marker="o", linewidth=1
    )
    axes[0, 1].set_title("Weekly Sales Trend")
    axes[0, 1].set_xlabel("Date")
    axes[0, 1].set_ylabel("Sales")

    # 3️⃣ Sales Distribution
    sns.histplot(
        df_product["Sales"], bins=20, kde=True, ax=axes[1, 0], color="lightcoral"
    )
    axes[1, 0].set_title("Sales Distribution (Histogram)")

    # 4️⃣ Rolling Mean & Std
    df_product["MA_4"] = df_product["Sales"].rolling(window=4, min_periods=1).mean()
    df_product["STD_4"] = df_product["Sales"].rolling(window=4, min_periods=1).std()
    axes[1, 1].plot(df_product.index, df_product["Sales"], label="Original", alpha=0.6)
    axes[1, 1].plot(
        df_product.index,
        df_product["MA_4"],
        label="4-Week MA",
        color="green",
        linewidth=2,
    )
    axes[1, 1].fill_between(
        df_product.index,
        df_product["MA_4"] - df_product["STD_4"],
        df_product["MA_4"] + df_product["STD_4"],
        color="green",
        alpha=0.1,
    )
    axes[1, 1].legend()
    axes[1, 1].set_title("Rolling Mean & Std (4 weeks)")

    # 5️⃣ ACF Plot
    n_obs = len(df_product["Sales"].dropna())
    max_lag = min(20, n_obs // 2)
    if max_lag > 1:
        plot_acf(
            df_product["Sales"].dropna(), ax=axes[2, 0], lags=max_lag, color="blue"
        )
        axes[2, 0].set_title(f"Autocorrelation (ACF) - Lags={max_lag}")
    else:
        axes[2, 0].text(0.3, 0.5, "Data terlalu pendek untuk ACF", fontsize=10)
        axes[2, 0].set_axis_off()

    # 6️⃣ Q-Q Plot
    stats.probplot(df_product["Sales"].dropna(), dist="norm", plot=axes[2, 1])
    axes[2, 1].set_title("Q-Q Plot (Normality)")

    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    plt.show()


# ============================================================================
# PREPROCESSING
# ============================================================================


def check_stationarity(series):
    result = adfuller(series.dropna(), autolag="AIC")
    return result[1] <= 0.05, result[1]


def make_stationary(df_product):
    series = df_product["Sales"]
    is_stat, pval = check_stationarity(series)
    if not is_stat:
        df_product["Sales_Diff"] = series.diff()
        is_stat_diff, _ = check_stationarity(df_product["Sales_Diff"].dropna())
        if is_stat_diff:
            return df_product, "Sales_Diff", 1
        df_product["Sales_Diff2"] = df_product["Sales_Diff"].diff()
        return df_product, "Sales_Diff2", 2
    return df_product, "Sales", 0


def clean_sales_data(df_long, product_name):
    df_product = df_long[df_long["Produk"] == product_name].copy()
    df_product = df_product.set_index("Date").sort_index()
    df_product["Sales"] = df_product["Sales"].interpolate(method="linear")
    Q1, Q3 = df_product["Sales"].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    df_product["Sales"] = df_product["Sales"].clip(lower, upper)
    return df_product


def clean_all_numeric(df_product):
    num_cols = df_product.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        # Interpolasi missing value
        df_product[col] = df_product[col].interpolate(method="linear")

        # Deteksi & potong outlier dengan IQR
        Q1, Q3 = df_product[col].quantile([0.25, 0.75])
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        df_product[col] = df_product[col].clip(lower, upper)
    return df_product


# ============================================================================
# EVALUASI PRODUK
# ============================================================================


def evaluate_product(df_product, original_series):
    """
    Mengevaluasi hasil pembersihan & transformasi data:
    - Statistik dasar (mean, std)
    - Jumlah outlier sebelum & sesudah
    - Status stasioneritas (ADF test)
    """
    # --- Statistik dasar setelah cleaning ---
    mean_val = df_product["Sales"].mean()
    std_val = df_product["Sales"].std()

    # --- Hitung outlier sebelum & sesudah cleaning ---
    Q1_before, Q3_before = original_series.quantile([0.25, 0.75])
    IQR_before = Q3_before - Q1_before
    lower_before, upper_before = (
        Q1_before - 1.5 * IQR_before,
        Q3_before + 1.5 * IQR_before,
    )
    outliers_before = (
        (original_series < lower_before) | (original_series > upper_before)
    ).sum()

    Q1_after, Q3_after = df_product["Sales"].quantile([0.25, 0.75])
    IQR_after = Q3_after - Q1_after
    lower_after, upper_after = Q1_after - 1.5 * IQR_after, Q3_after + 1.5 * IQR_after
    outliers_after = (
        (df_product["Sales"] < lower_after) | (df_product["Sales"] > upper_after)
    ).sum()

    # --- Uji stasioneritas (ADF Test) ---
    try:
        adf_result = adfuller(df_product["Sales"].dropna(), autolag="AIC")
        p_value = round(adf_result[1], 6)
        stationary = "Stationary" if p_value <= 0.05 else "Non-stationary"
    except Exception:
        p_value = None
        stationary = "Error (Data terlalu sedikit)"

    # --- Return hasil evaluasi dalam dict ---
    return {
        "Mean": mean_val,
        "Std": std_val,
        "Outlier Before": int(outliers_before),
        "Outlier After": int(outliers_after),
        "Stationary": stationary,
        "p-value (ADF)": p_value,
    }


def summarize_arima_readiness(df_product, col, d):
    """
    Menampilkan ringkasan kesiapan data untuk tahap ARIMA modeling.
    Fokus ke stasioneritas, jumlah data, dan parameter differencing.
    """
    print("\nPREPROCESSING SELESAI - SUMMARY")
    print("======================================================================")
    print(f"✓ Jumlah data: {len(df_product)} minggu")
    print(f"✓ Missing values: {df_product.isna().sum().sum()}")
    print(f"✓ Nilai negatif: {(df_product[col] < 0).sum()}")

    if d == 0:
        print("✓ Stasioneritas: Sudah stasioner (d=0)")
    elif d == 1:
        print("✓ Stasioneritas: Perlu differencing (d=1)")
    else:
        print("✓ Stasioneritas: Perlu differencing lebih lanjut (d=2)")

    print(f"✓ Series untuk ARIMA: {col}")
    print(f"✓ Rekomendasi parameter d: {d}")
    print("\n[NEXT STEP] Data siap untuk ARIMA modeling dengan parameter d =", d)


# ============================================================================
# GUI
# ============================================================================


class ARIMAGUI:
    def __init__(self, root, df_long):
        self.root = root
        self.df_long = df_long

        root.title("ARIMA Preprocessing - Multi Product Viewer")
        root.geometry("600x420")

        # === PILIH PRODUK ===
        ttk.Label(root, text="Pilih Produk:", font=("Arial", 11, "bold")).pack(pady=10)
        produk_values = df_long["Produk"].dropna().astype(str).unique()
        self.combo = ttk.Combobox(root, values=sorted(produk_values), width=60)
        self.combo.pack(pady=5)

        # === PILIH MODE ===
        ttk.Label(root, text="Pilih Mode Analisis:", font=("Arial", 10, "bold")).pack(
            pady=5
        )
        self.mode = ttk.Combobox(
            root, values=["Visualisasi", "Evaluasi", "Keduanya"], width=30
        )
        self.mode.set("Keduanya")  # default mode
        self.mode.pack(pady=5)

        ttk.Button(root, text="Jalankan", command=self.run_analysis).pack(pady=10)

        # === AREA LOG ===
        self.log_text = tk.Text(root, height=12, width=70, bg="#f0f0f0")
        self.log_text.pack(pady=10)
        self.log("Aplikasi siap. Silakan pilih produk dan mode analisis.")

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def run_analysis(self):
        product_name = self.combo.get()
        mode = self.mode.get()

        if not product_name:
            messagebox.showwarning(
                "Peringatan", "Silakan pilih produk terlebih dahulu!"
            )
            return

        self.log(f"🔍 Memproses produk: {product_name}")

        # Simpan data original untuk perbandingan evaluasi
        original_series = self.df_long[self.df_long["Produk"] == product_name][
            "Sales"
        ].copy()

        # Bersihkan data dan buat stasioner
        df_product = clean_sales_data(self.df_long, product_name)
        df_product = clean_all_numeric(df_product)
        df_product, col, d = make_stationary(df_product)

        # === MODE: VISUALISASI ===
        if mode in ["Visualisasi", "Keduanya"]:
            visualize_product(df_product, product_name)

        # === MODE: EVALUASI ===
        if mode in ["Evaluasi", "Keduanya"]:
            eval_result = evaluate_product(df_product, original_series)
            self.log(f"📊 Evaluasi Data untuk {product_name}:")
            for k, v in eval_result.items():
                self.log(f"   - {k}: {v}")

            # Tambahan: tampilkan ringkasan ARIMA readiness di terminal
            summarize_arima_readiness(df_product, col, d)

        self.log(f"✅ Analisis selesai untuk {product_name} (d={d})")


# ============================================================================
# MAIN
# ============================================================================


def main():
    print("Loading dataset...")
    df = pd.read_excel("AVG 12W & 5W (W1-W40).xlsx", header=None)
    header_row = df[
        df.astype(str)
        .apply(lambda x: x.str.contains("Kode Produk", case=False))
        .any(axis=1)
    ].index[0]
    df = pd.read_excel("AVG 12W & 5W (W1-W40).xlsx", header=header_row)
    df = df.loc[:, ~df.columns.duplicated()]

    week_cols = [c for c in df.columns if str(c).isdigit()]
    df_long = df.melt(
        id_vars=["PRINC 1", "Kode Produk", "Produk"],
        value_vars=week_cols,
        var_name="Week",
        value_name="Sales",
    )

    start_date = pd.Timestamp("2024-01-01")
    df_long["Date"] = df_long["Week"].apply(
        lambda x: start_date + pd.to_timedelta((int(x) - 1) * 7, unit="D")
    )
    df_long = df_long.sort_values(["Produk", "Date"])

    root = tk.Tk()
    app = ARIMAGUI(root, df_long)
    root.mainloop()


if __name__ == "__main__":
    main()
