"""
audit_outlier_deep.py
Jalankan dari folder: arima-dashboard/backend/
  python audit_outlier_deep.py

Tujuan: cari penyebab perbedaan outlier_before notebook vs API.
Menguji tiga hipotesis:
  H1 — backend menghitung IQR pada data post-winsorize (bukan pre)
  H2 — set SKU per family berbeda antara notebook dan backend
  H3 — panjang series per SKU berbeda (week count)
"""

import sys, pandas as pd, numpy as np
sys.path.insert(0, '.')   # supaya bisa import services.arima_service

from pathlib import Path
DATA_PATH = Path(__file__).resolve().parent / "AVG 12W & 5W.csv"

# ── helpers ──────────────────────────────────────────────────────────────────

def extract_family(name):
    n = str(name).upper()
    if n.startswith("5DAYS"):     return "5DAYS"
    if n.startswith("CAF"):       return "CAF"
    if n.startswith("FOX"):       return "FOX"
    if n.startswith("HYDROPLUS"): return "HYDROPLUS"
    if n.startswith("ROYO"):      return "ROYO"
    if n.startswith("TUBRUK"):    return "TUBRUK"
    if n.startswith("UHT"):       return "UHT"
    return "OTHER"

def winsorize_series(s):
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return s.clip(lower=q1 - 1.5*iqr, upper=q3 + 1.5*iqr)

def count_outliers_iqr(s):
    s = pd.Series(s).dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return int(((s < q1 - 1.5*iqr) | (s > q3 + 1.5*iqr)).sum())

# ── rebuild notebook pipeline ────────────────────────────────────────────────

df_raw   = pd.read_csv(DATA_PATH, header=None, encoding="utf-8-sig")
df_clean = df_raw.iloc[3:].reset_index(drop=True)
headers  = df_clean.iloc[0].tolist()
df_data  = df_clean.iloc[1:].reset_index(drop=True)

col_product = 2
weeks, week_col_indices = [], []
for i, h in enumerate(headers):
    try:
        w = float(h)
        if 1 <= w <= 40:
            weeks.append(int(w)); week_col_indices.append(i)
    except: pass

data_list = []
for _, row in df_data.iterrows():
    product = row[col_product]
    if pd.isna(product) or product == "": continue
    for wn, ci in zip(weeks, week_col_indices):
        s = row[ci]
        if pd.notna(s) and s != "":
            try: data_list.append({"Product": product, "Week": wn, "Sales": float(s)})
            except: pass

df_long = pd.DataFrame(data_list).sort_values(["Product","Week"]).reset_index(drop=True)
actual_weeks = sorted(df_long["Week"].unique())

full_data = []
for p in df_long["Product"].unique():
    df_p = df_long[df_long["Product"]==p].copy()
    fw   = pd.DataFrame({"Week": actual_weeks})
    df_f = fw.merge(df_p[["Week","Sales"]], on="Week", how="left")
    df_f["Product"] = p
    full_data.append(df_f)
df_full_long = pd.concat(full_data, ignore_index=True)

df_full_long["Sales"] = (
    df_full_long.groupby("Product")["Sales"]
    .transform(lambda s: s.interpolate(method="linear", limit_direction="both"))
)
df_full_long["Sales"] = df_full_long["Sales"].fillna(0)

# Simpan snapshot PRE-winsorize (ini yang notebook pakai untuk hitung outlier)
df_pre_winsorize = df_full_long.copy()
df_pre_winsorize["Family"] = df_pre_winsorize["Product"].apply(extract_family)

# Notebook: hitung outlier SEBELUM clip
notebook_outliers_per_sku = {}
for product in df_full_long["Product"].unique():
    mask   = df_full_long["Product"] == product
    series = df_full_long.loc[mask, "Sales"]
    notebook_outliers_per_sku[product] = count_outliers_iqr(series)
    df_full_long.loc[mask, "Sales"] = winsorize_series(series)

df_full_long["Family"] = df_full_long["Product"].apply(extract_family)
last_week = df_full_long["Week"].max()
df_full_long_nb = df_full_long[df_full_long["Week"] != last_week].copy()

# Sum per family (notebook)
TARGET = ["5DAYS","CAF","FOX","HYDROPLUS","TUBRUK","UHT"]
notebook_by_family = {}
for fam in TARGET:
    skus = df_full_long_nb[df_full_long_nb["Family"]==fam]["Product"].unique()
    notebook_by_family[fam] = sum(notebook_outliers_per_sku.get(p,0) for p in skus)

# ── ambil backend pipeline cache ─────────────────────────────────────────────

from services.arima_service import _build_pipeline, get_data_preparation
pipe       = _build_pipeline()
df_backend = pipe["df_full_long"]   # post-winsorize, post-drop-last-week

# ── H2: set SKU per family ────────────────────────────────────────────────────

print("=" * 70)
print("H2: Apakah set SKU per family sama?")
print("=" * 70)
h2_fail = False
for fam in TARGET:
    nb_skus = set(df_full_long_nb[df_full_long_nb["Family"]==fam]["Product"].unique())
    be_skus = set(df_backend[df_backend["Family"]==fam]["Product"].unique())
    match   = nb_skus == be_skus
    if not match:
        h2_fail = True
    print(f"  {fam:<12} {'✅' if match else '❌'}  nb={len(nb_skus)}  be={len(be_skus)}", end="")
    if nb_skus - be_skus: print(f"  only_nb={nb_skus - be_skus}", end="")
    if be_skus - nb_skus: print(f"  only_be={be_skus - nb_skus}", end="")
    print()
print(f"\nH2 result: {'❌ SKU SET BERBEDA' if h2_fail else '✅ SKU set identik'}")

# ── H3: panjang series per SKU ────────────────────────────────────────────────

print()
print("=" * 70)
print("H3: Apakah panjang series (week count) per SKU sama?")
print("=" * 70)
h3_fail = False
for fam in TARGET:
    nb_df   = df_full_long_nb[df_full_long_nb["Family"]==fam]
    be_df   = df_backend[df_backend["Family"]==fam]
    nb_wks  = nb_df.groupby("Product")["Week"].count()
    be_wks  = be_df.groupby("Product")["Week"].count()
    common  = set(nb_wks.index) & set(be_wks.index)
    diffs   = {p: (nb_wks[p], be_wks[p]) for p in common if nb_wks[p] != be_wks[p]}
    match   = len(diffs) == 0
    if not match: h3_fail = True
    print(f"  {fam:<12} {'✅' if match else '❌'}", end="")
    if diffs: print(f"  mismatches={diffs}", end="")
    print()
print(f"\nH3 result: {'❌ PANJANG SERIES BERBEDA' if h3_fail else '✅ Panjang series identik'}")

# ── H1: pre vs post winsorize ─────────────────────────────────────────────────

print()
print("=" * 70)
print("H1: Backend hitung IQR pada data pre- atau post-winsorize?")
print("Spot check per SKU untuk semua family — bandingkan nilai series")
print("=" * 70)

# Untuk setiap family, ambil satu SKU dan cek apakah series backend
# cocok dengan pre-winsorize atau post-winsorize notebook
for fam in TARGET:
    nb_skus = list(df_full_long_nb[df_full_long_nb["Family"]==fam]["Product"].unique())
    if not nb_skus: continue
    sku = nb_skus[0]

    nb_pre  = df_pre_winsorize[df_pre_winsorize["Product"]==sku]["Sales"].sort_values(ignore_index=True)
    nb_post = df_full_long_nb[df_full_long_nb["Product"]==sku]["Sales"].sort_values(ignore_index=True)
    be_ser  = df_backend[df_backend["Product"]==sku]["Sales"].sort_values(ignore_index=True)

    # Potong ke panjang yang sama untuk perbandingan
    min_len = min(len(nb_pre), len(nb_post), len(be_ser))
    pre_v   = nb_pre.values[:min_len]
    post_v  = nb_post.values[:min_len]
    be_v    = be_ser.values[:min_len]

    close_pre  = np.allclose(pre_v,  be_v, atol=0.01)
    close_post = np.allclose(post_v, be_v, atol=0.01)

    oc_pre  = count_outliers_iqr(nb_pre)
    oc_post = count_outliers_iqr(nb_post)
    oc_be   = count_outliers_iqr(be_ser)

    print(f"\n  {fam} / SKU: {sku}")
    print(f"    series match pre-winsorize?  {close_pre}")
    print(f"    series match post-winsorize? {close_post}")
    print(f"    outlier(pre)={oc_pre}  outlier(post)={oc_post}  outlier(backend)={oc_be}")

# ── Tabel akhir ───────────────────────────────────────────────────────────────

print()
print("=" * 70)
print("TABEL AKHIR: Notebook vs API")
print("=" * 70)
print(f"{'Family':<12} {'Notebook':>10} {'API':>10} {'Match?':>8}")
print("-" * 44)
for fam in TARGET:
    r   = get_data_preparation(fam)
    nb  = notebook_by_family[fam]
    be  = r["outliers_before"]
    print(f"{fam:<12} {nb:>10} {be:>10} {'✅' if nb == be else '❌':>8}")

print()
print("SELESAI.")
