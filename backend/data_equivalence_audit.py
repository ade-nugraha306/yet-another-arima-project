"""
data_equivalence_audit.py
─────────────────────────
Compares the final preprocessed series from:
  A) backend/ARIMA_TA_CSV.ipynb  (Cell 3–17 pipeline)
  B) arima_service._get_family_df()

For families: HYDROPLUS, TUBRUK, UHT

Runs in nicky-env:
  /home/ade-nugraha/miniconda3/envs/nicky-env/bin/python data_equivalence_audit.py
"""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
from pathlib import Path

ROOT      = Path(__file__).resolve().parent
DATA_PATH = ROOT / "AVG 12W & 5W.csv"
FAMILIES  = ["HYDROPLUS", "TUBRUK", "UHT"]

# ──────────────────────────────────────────────────────────
# PIPELINE A — Exact Notebook (Cell 3–17)
# ──────────────────────────────────────────────────────────

def pipeline_notebook() -> dict[str, np.ndarray]:
    """Reproduce Cell 3–17 of backend/ARIMA_TA_CSV.ipynb verbatim."""

    # Cell 3
    df_raw = pd.read_csv(DATA_PATH, header=None)

    # Cell 5
    df_clean = df_raw.iloc[3:].reset_index(drop=True)
    headers  = df_clean.iloc[0].tolist()
    df_data  = df_clean.iloc[1:].reset_index(drop=True)

    col_product = 2

    weeks, week_col_indices = [], []
    for col_idx, header in enumerate(headers):
        try:
            week_num = float(header)
            if 1 <= week_num <= 40:
                weeks.append(int(week_num))
                week_col_indices.append(col_idx)
        except (ValueError, TypeError):
            pass

    # Build long dataframe (notebook iterates rows)
    rows = []
    for _, row in df_data.iterrows():
        product = row.iloc[col_product]
        if pd.isna(product) or str(product).strip() == "":
            continue
        for w, c_idx in zip(weeks, week_col_indices):
            try:
                raw_val = row.iloc[c_idx]
                val = float(str(raw_val).replace(",", ".")) if pd.notna(raw_val) else np.nan
            except Exception:
                val = np.nan
            rows.append({"Product": product, "Week": w, "Sales": val})

    df_full_long = pd.DataFrame(rows)

    # Cell 11 — interpolate per product
    df_full_long["Sales"] = (
        df_full_long
        .groupby("Product")["Sales"]
        .transform(lambda s: s.interpolate(method="linear", limit_direction="both"))
    )
    df_full_long["Sales"] = df_full_long["Sales"].fillna(0)

    # Cell 13 — fix_internal_zeros: DISABLED (per notebook comment)

    # Cell 14 — winsorize per product (IQR)
    def winsorize_series(series):
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        return series.clip(lower=q1 - 1.5 * iqr, upper=q3 + 1.5 * iqr)

    for product in df_full_long["Product"].unique():
        mask = df_full_long["Product"] == product
        df_full_long.loc[mask, "Sales"] = winsorize_series(df_full_long.loc[mask, "Sales"])

    # Cell 16 — extract family
    def extract_family(n):
        n = str(n).upper()
        if n.startswith("5DAYS"):     return "5DAYS"
        elif n.startswith("CAF"):     return "CAF"
        elif n.startswith("FOX"):     return "FOX"
        elif n.startswith("HYDROPLUS"): return "HYDROPLUS"
        elif n.startswith("ROYO"):    return "ROYO"
        elif n.startswith("TUBRUK"):  return "TUBRUK"
        elif n.startswith("UHT"):     return "UHT"
        return "OTHER"

    df_full_long["Family"] = df_full_long["Product"].apply(extract_family)

    # Cell 17 — drop last week, aggregate to family level
    last_week = df_full_long["Week"].max()
    df_full_long = df_full_long[df_full_long["Week"] != last_week].copy()

    df_family = (
        df_full_long
        .groupby(["Family", "Week"], as_index=False)["Sales"]
        .sum()
    )

    # Cell 18 — MIN_FAMILY_AVG filter (not needed for our 3 families but run anyway)
    family_stats = df_family.groupby("Family")["Sales"].agg(["mean","sum"]).reset_index()
    valid_families = family_stats[family_stats["mean"] >= 5]["Family"].tolist()
    df_family = df_family[df_family["Family"].isin(valid_families)].copy()

    result = {}
    for family in FAMILIES:
        df_f = df_family[df_family["Family"] == family].sort_values("Week")
        result[family] = df_f[["Week", "Sales"]].reset_index(drop=True)

    return result


# ──────────────────────────────────────────────────────────
# PIPELINE B — Backend arima_service._get_family_df()
# ──────────────────────────────────────────────────────────

def pipeline_backend() -> dict[str, pd.DataFrame]:
    sys.path.insert(0, str(ROOT))
    if "services.arima_service" in sys.modules:
        del sys.modules["services.arima_service"]
    from backend.services import arima_service as svc
    svc._df_raw_cache    = None
    svc._df_family_cache = {}

    result = {}
    for family in FAMILIES:
        df = svc._get_family_df(family)
        # _get_family_df returns [Week, Date, Sales] — drop Date
        df_out = df[["Week", "Sales"]].reset_index(drop=True)
        result[family] = df_out
    return result


# ──────────────────────────────────────────────────────────
# COMPARISON
# ──────────────────────────────────────────────────────────

def compare(nb: dict, be: dict):
    all_identical = True

    for family in FAMILIES:
        nb_df = nb[family].copy()
        be_df = be[family].copy()

        print(f"\n{'═'*70}")
        print(f"  FAMILY: {family}")
        print(f"{'═'*70}")

        # Summary stats
        print(f"\n  {'Metric':10} {'Notebook':>14} {'Backend':>14}  Match?")
        print(f"  {'─'*50}")
        for metric in ["n_obs", "mean", "std", "min", "max"]:
            nb_s = nb_df["Sales"]
            be_s = be_df["Sales"]
            if metric == "n_obs":
                nv, bv = len(nb_s), len(be_s)
                match = nv == bv
                print(f"  {metric:10} {nv:>14} {bv:>14}  {'✅' if match else '❌'}")
            else:
                fn = {"mean": np.mean, "std": np.std, "min": np.min, "max": np.max}[metric]
                nv, bv = fn(nb_s), fn(be_s)
                match = abs(nv - bv) < 1e-6
                print(f"  {metric:10} {nv:>14.6f} {bv:>14.6f}  {'✅' if match else '❌ Δ='+f'{abs(nv-bv):.6f}'}")

        # Week-by-week comparison
        if len(nb_df) != len(be_df):
            print(f"\n  ❌ Length mismatch — cannot do week comparison ({len(nb_df)} vs {len(be_df)})")
            all_identical = False
            continue

        merged = nb_df.copy()
        merged.columns = ["Week", "NB_Sales"]
        merged["BE_Sales"] = be_df["Sales"].values
        merged["Diff"] = merged["NB_Sales"] - merged["BE_Sales"]
        merged["AbsDiff"] = merged["Diff"].abs()

        diffs = merged[merged["AbsDiff"] > 1e-6]

        if diffs.empty:
            print(f"\n  ✅ ALL {len(merged)} WEEKS IDENTICAL (max diff = 0.000000)")
        else:
            all_identical = False
            print(f"\n  ❌ {len(diffs)} WEEKS DIFFER (out of {len(merged)})")
            print(f"\n  {'Week':>5} | {'Notebook':>14} | {'Backend':>14} | {'Diff':>12}")
            print(f"  {'─'*55}")
            for _, row in diffs.iterrows():
                print(f"  W{int(row['Week']):>3}   | {row['NB_Sales']:>14.6f} | {row['BE_Sales']:>14.6f} | {row['Diff']:>+12.6f}")

            # First differing week stage analysis
            first = diffs.iloc[0]
            print(f"\n  ── First diff: W{int(first['Week'])} | NB={first['NB_Sales']:.6f} | BE={first['BE_Sales']:.6f}")

    print(f"\n{'═'*70}")
    print("KESIMPULAN DATA EQUIVALENCE")
    print(f"{'═'*70}")
    if all_identical:
        print("✅ Series IDENTIK untuk semua family yang dicek.")
        print("   Root cause BUKAN pada data loading/preprocessing.")
        print("   Kemungkinan penyebab: versi pmdarima / random state auto_arima.")
    else:
        print("❌ Series TIDAK IDENTIK.")
        print("   Root cause ada pada tahap preprocessing.")
    print()
    return all_identical


# ──────────────────────────────────────────────────────────
# STEP-BY-STEP STAGE BISECTION (jika series berbeda)
# ──────────────────────────────────────────────────────────

def bisect_stage(family: str):
    """Identify which stage first introduces a difference for one family."""
    print(f"\n{'─'*70}")
    print(f"  BISECTION AUDIT: {family}")
    print(f"{'─'*70}")

    # Load raw notebook
    df_raw = pd.read_csv(DATA_PATH, header=None)
    df_clean = df_raw.iloc[3:].reset_index(drop=True)
    headers  = df_clean.iloc[0].tolist()
    df_data  = df_clean.iloc[1:].reset_index(drop=True)

    col_product = 2
    weeks, week_col_indices = [], []
    for col_idx, header in enumerate(headers):
        try:
            week_num = float(header)
            if 1 <= week_num <= 40:
                weeks.append(int(week_num))
                week_col_indices.append(col_idx)
        except: pass

    rows_nb = []
    for _, row in df_data.iterrows():
        product = row.iloc[col_product]
        if pd.isna(product) or str(product).strip() == "": continue
        for w, c_idx in zip(weeks, week_col_indices):
            try:
                val = float(str(row.iloc[c_idx]).replace(",",".")) if pd.notna(row.iloc[c_idx]) else np.nan
            except: val = np.nan
            rows_nb.append({"Product": product, "Week": w, "Sales": val})

    df_nb = pd.DataFrame(rows_nb)

    # Load raw backend
    sys.path.insert(0, str(ROOT))
    if "services.arima_service" in sys.modules: del sys.modules["services.arima_service"]
    from backend.services import arima_service as svc
    svc._df_raw_cache = None; svc._df_family_cache = {}
    df_be_raw = svc._load_raw_long()

    # Filter to family products
    def extract_family(n):
        n = str(n).upper()
        if n.startswith("5DAYS"): return "5DAYS"
        elif n.startswith("CAF"): return "CAF"
        elif n.startswith("FOX"): return "FOX"
        elif n.startswith("HYDROPLUS"): return "HYDROPLUS"
        elif n.startswith("ROYO"): return "ROYO"
        elif n.startswith("TUBRUK"): return "TUBRUK"
        elif n.startswith("UHT"): return "UHT"
        return "OTHER"

    df_nb["Family"] = df_nb["Product"].apply(extract_family)
    nb_fam = df_nb[df_nb["Family"] == family].copy()
    be_fam = df_be_raw[df_be_raw["Family"] == family].copy()

    nb_products = sorted(nb_fam["Product"].unique())
    be_products = sorted(be_fam["Produk"].unique() if "Produk" in be_fam.columns else be_fam["Product"].unique() if "Product" in be_fam.columns else [])

    print(f"\n  Products in family:")
    print(f"    Notebook: {nb_products[:5]}{'...' if len(nb_products)>5 else ''} ({len(nb_products)} total)")
    print(f"    Backend:  {be_products[:5]}{'...' if len(be_products)>5 else ''} ({len(be_products)} total)")

    # Stage 1: LOADING — compare raw values for first SKU
    nb_skus = sorted(nb_fam["Product"].unique())
    be_col  = "Produk" if "Produk" in be_fam.columns else "Product"
    be_skus = sorted(be_fam[be_col].unique())

    print(f"\n  STAGE 1 — LOADING (raw, before interpolation)")
    for sku in nb_skus[:2]:  # check first 2 SKUs
        nb_sku = nb_fam[nb_fam["Product"]==sku].sort_values("Week")["Sales"].values
        be_sku = be_fam[be_fam[be_col]==sku].sort_values("Week")["Sales"].values if sku in be_skus else None
        if be_sku is None:
            print(f"    SKU '{sku}': NOT FOUND in backend")
            continue
        n_diff = np.sum(np.abs(nb_sku - be_sku[:len(nb_sku)]) > 1e-4) if len(nb_sku)==len(be_sku) else -1
        print(f"    SKU '{sku[:30]:30}': n_diff={n_diff}, NB_mean={np.nanmean(nb_sku):.4f}, BE_mean={np.nanmean(be_sku):.4f}")


if __name__ == "__main__":
    print("Running notebook pipeline...")
    nb_data = pipeline_notebook()
    print("Running backend pipeline...")
    be_data = pipeline_backend()

    identical = compare(nb_data, be_data)

    if not identical:
        print("\nRunning bisection to find differing stage...")
        for fam in FAMILIES:
            # check if this family's series differ
            nb_s = nb_data[fam]["Sales"].values
            be_s = be_data[fam]["Sales"].values
            if len(nb_s) == len(be_s) and np.max(np.abs(nb_s - be_s)) > 1e-6:
                bisect_stage(fam)
            elif len(nb_s) != len(be_s):
                print(f"\n{fam}: length mismatch — {len(nb_s)} vs {len(be_s)}")
