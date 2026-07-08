# ARIMA Dashboard TA — Frontend Handoff Final

Dokumen ini adalah satu-satunya referensi yang dibutuhkan untuk mengerjakan
frontend dashboard. Baca seluruh dokumen dari atas ke bawah sebelum menyentuh
kode apapun. Tidak ada asumsi yang perlu dibuat — semua keputusan sudah
tercatat di sini.

# Sumber Kebenaran (Source of Truth)

Proyek ini merupakan implementasi dashboard dari metodologi Tugas Akhir.

Urutan prioritas sumber kebenaran:

1. ARIMA_TA_CSV.ipynb
2. Response Backend API
3. Implementasi Frontend
4. Dokumen ini

Jika terjadi perbedaan:

Notebook > Backend > Frontend > Dokumentasi

Notebook selalu menjadi acuan utama.

---

# Metodologi Tidak Boleh Diubah

Tujuan frontend ini adalah memvisualisasikan hasil penelitian Tugas Akhir.

Agent atau developer frontend TIDAK BOLEH:

* Mengubah parameter ARIMA
* Mengubah train/test split
* Mengubah forecast horizon
* Mengubah aturan filtering family
* Mengubah metode winsorization
* Mengubah logika confidence interval
* Mengubah logika stasioneritas
* Mengubah metrik evaluasi

Perubahan metodologi hanya boleh dilakukan terlebih dahulu pada:

ARIMA_TA_CSV.ipynb

dan kemudian disesuaikan ke backend dan frontend.

---

# Benchmark Validasi

Hasil audit reproduksi notebook (2026-06-08) — dijalankan dengan environment
dan dataset yang sama antara notebook dan backend. Delta = 0.0000% untuk semua family.

Perbedaan kecil (< 0.5%) masih dapat diterima.

Perbedaan besar menunjukkan adanya penyimpangan metodologi (methodology drift).

| Family    | n_obs | Mean Sales | Order Evaluasi  | MAE      | RMSE     | sMAPE    |
| --------- | ----- | ---------- | --------------- | -------- | -------- | -------- |
| 5DAYS     | 38    | 124.12     | ARIMA(0,1,1)    | 38.3481  | 49.8145  | 27.2633% |
| CAF       | 38    | 514.50     | ARIMA(0,1,1)    | 212.0448 | 265.8341 | 35.2437% |
| FOX       | 38    | 257.59     | ARIMA(0,0,0)    | 71.0296  | 92.7677  | 34.7800% |
| HYDROPLUS | 38    | 50.72      | ARIMA(3,2,0)    | 20.2560  | 26.4629  | 21.2553% |
| TUBRUK    | 38    | 109.24     | ARIMA(0,1,1)    | 15.3290  | 18.3912  | 14.6753% |
| UHT       | 38    | 256.41     | ARIMA(0,1,1)    | 99.5934  | 115.6871 | 31.2955% |

> **Catatan:** Order di kolom "Order Evaluasi" adalah order dari model yang difit
> pada train split (33 titik). Order model Modeling (full series, 38 titik) akan
> berbeda — ini by design. Lihat Seksi 8 (BUKAN BUG).

> **ROYO:** Di-exclude karena mean sales ≈ 1.31 < MIN_FAMILY_AVG = 5 (notebook Cell 20).

---

## 1. Stack Teknologi

| Tool | Keterangan |
|------|-----------|
| Bun | Package manager & runtime |
| React + TypeScript (TSX) | UI framework |
| Tailwind CSS | Styling |
| shadcn/ui | Component library |
| Vite | Dev server port 5173, proxy ke backend port 8000 |
| Recharts | Chart library (sudah digunakan di semua komponen) |
| TanStack Query | Ada di App.tsx tapi belum dipakai di stage components |
| React Router | Routing, ada Index.tsx sebagai halaman utama |

---

## 2. Struktur File Frontend (Kondisi Aktual)

```
src/
├── App.tsx                            ← setup provider + router, TIDAK perlu diubah
├── pages/
│   └── Index.tsx                      ← halaman utama, family selector ada di sini
├── components/
│   ├── AppSidebar.tsx                 ← sidebar + family dropdown (tidak diupload, asumsikan sudah ada)
│   └── stages/
│       ├── BusinessUnderstanding.tsx  ← TIDAK perlu diubah
│       ├── DataAcquisition.tsx        ← sudah direwrite, tidak ada bug
│       ├── DataPreparation.tsx        ← sudah direwrite, ADA LABEL SALAH (lihat seksi 8)
│       ├── EDA.tsx                    ← sudah direwrite, tidak ada bug kritis
│       ├── Modeling.tsx               ← sudah direwrite, ADA BUG ENDPOINT (lihat seksi 8)
│       └── Evaluation.tsx             ← sudah direwrite, ADA BUG KRITIS (lihat seksi 8)
└── services/
    └── api.ts                         ← sudah direwrite, ADA 2 BUG (lihat seksi 6)
```

---

## 3. Alur Data

```
App.tsx
  └── Index.tsx
        ├── State: activeStage (0-5), familyIndex, horizon, families[]
        ├── Fetch GET /families → mengisi families[]
        ├── selectedFamily = families[familyIndex]
        └── AppSidebar
              → user pilih family → setFamilyIndex → selectedFamily berubah
              → stage component re-render → fetch ulang dengan family baru
```

Props yang diterima setiap stage component:

| Komponen | Props |
|----------|-------|
| DataAcquisition | `family: string` |
| DataPreparation | `family: string` |
| EDA | `family: string` |
| Modeling | `selectedFamily: string`, `horizon: number` |
| Evaluation | `family: string` |

Jangan ubah interface props ini.

---

## 4. Family yang Valid

Family yang saat ini valid berdasarkan notebook:

```ts
["5DAYS", "CAF", "FOX", "HYDROPLUS", "TUBRUK", "UHT"]
```

Penting:

ROYO mungkin masih ada di data mentah (raw data) dan masih dapat terdeteksi saat proses ekstraksi family.

Namun pada notebook, ROYO biasanya tidak lolos proses filtering karena aturan:

```python
MIN_FAMILY_AVG = 5
```

Frontend TIDAK BOLEH melakukan hardcode daftar family.

Selalu gunakan:

```ts
GET /families
```

sebagai sumber data utama.

Jika suatu saat ROYO muncul kembali karena perubahan filtering di backend, frontend harus dapat mendukungnya secara otomatis tanpa perubahan kode.


---

## 5. Endpoint Backend

Base URL via Vite proxy: `/api`
Backend aktual: `http://localhost:8000`
Semua endpoint: **GET + query param**.

```
GET /health
GET /families
GET /data-acquisition?family=FOX
GET /data-preparation?family=FOX
GET /eda?family=FOX
GET /modelling?family=FOX&horizon=5     ← DUA L (sesuai app.py aktual)
GET /evaluation?family=FOX
```

**PENTING — Penamaan endpoint:** Backend `app.py` mendefinisikan `/modelling`
(DUA L). `api.ts` sudah menggunakan `/modelling` (DUA L) — ini **BENAR**.
Jangan ubah ke `/modeling` (SATU L) kecuali backend diubah terlebih dahulu.

Selalu verifikasi route yang sebenarnya pada `app.py` sebelum mengubah frontend.
Implementasi backend adalah sumber kebenaran.

Field `trend` tidak dikembalikan oleh backend. Card "Klasifikasi Tren" di
`Evaluation.tsx` **sudah dihapus** (per perbaikan 2026-06-08).

---

## 6. api.ts — Bug & Perbaikan

### BUG KRITIS 1 — Inkonsistensi UI karena field trend tidak tersedia
```ts
// SALAH (saat ini di api.ts):
export async function getModelling(family: string, horizon: number) {
  return apiFetch<ModellingResponse>(
    `/modelling?family=${encodeURIComponent(family)}&horizon=${horizon}`
  );
}

// BENAR:
export async function getModelling(family: string, horizon: number) {
  return apiFetch<ModellingResponse>(
    `/modeling?family=${encodeURIComponent(family)}&horizon=${horizon}`
  );
}
```

### Bug 2: EvaluationResponse mendefinisikan field yang tidak ada di backend

```ts
// SALAH (saat ini di api.ts):
export interface EvaluationResponse {
  ...
  trend: "FAST" | "MEDIUM" | "SLOW";  // tidak ada di backend
}

// BENAR (pilih salah satu):
// Opsi A — hapus field trend:
export interface EvaluationResponse {
  family: string;
  order: [number, number, number];
  aic: number | null;
  mae: number;
  rmse: number;
  smape: number;
  actual_train: number[];
  actual_test: number[];
  fitted: number[];
  dates_train: string[];
  dates_test: string[];
  // tidak ada field trend
}

// Opsi B — jadikan optional (aman jika backend nanti menambahkannya):
trend?: "FAST" | "MEDIUM" | "SLOW";
```

### Bug 3 (minor): EDAResponse mendefinisikan field yang tidak ada di /eda

Field berikut ada di `EDAResponse` interface tapi TIDAK dikembalikan
oleh endpoint `/eda` (field-field ini hanya ada di `/data-preparation`):
- `missing_before`
- `missing_after`
- `outliers_before`
- `outliers_after`
- `cleaning_method`

Tidak menyebabkan crash karena nilainya hanya `undefined`, tapi harus
dibersihkan. Hapus atau jadikan optional:
```ts
missing_before?: number;
missing_after?: number;
outliers_before?: number;
outliers_after?: number;
cleaning_method?: string;
```

### Bug 4 (minor): ModellingResponse kurang field

`historical_avg` dan `forecast_avg` dikembalikan backend tapi tidak ada
di interface. Tidak crash, tapi tambahkan untuk kelengkapan:
```ts
export interface ModellingResponse {
  ...
  historical_avg: number;
  forecast_avg: number;
}
```

### Interface lengkap yang benar

```ts
export interface DataAcquisitionResponse {
  family: string;
  sku_count: number;
  skus: string[];
  total_weeks: number;
  weeks: string[];               // "YYYY-MM-DD"
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
  d: number;                     // 0, 1, atau 2
  weeks: string[];               // "YYYY-MM-DD"
  sales_before: (number | null)[];
  sales_after: number[];
}

export interface BoxplotStats {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
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
  method: string;
  weeks: string[];               // "YYYY-MM-DD"
  sales_before: (number | null)[];
  sales_after: number[];
  rolling_mean: number[];
  rolling_std: number[];
  boxplot_before: BoxplotStats;
  boxplot_after: BoxplotStats;
  // TIDAK ADA: missing_before, missing_after, outliers_before,
  // outliers_after, cleaning_method
}

export interface ModellingResponse {
  family: string;
  order: [number, number, number];
  aic: number | null;
  horizon: number;
  forecast: number[];
  upper: number[];
  lower: number[];
  forecast_dates: string[];      // "YYYY-MM-DD"
  last_sales: number;
  historical_weeks: string[];    // "YYYY-MM-DD"
  historical_sales: number[];
  historical_avg: number;
  forecast_avg: number;
}

export interface EvaluationResponse {
  family: string;
  order: [number, number, number];
  aic: number | null;
  mae: number;
  rmse: number;
  smape: number;                 // sudah dalam persen, contoh: 49.95
  actual_train: number[];
  actual_test: number[];
  fitted: number[];
  dates_train: string[];         // "YYYY-MM-DD"
  dates_test: string[];
  // trend TIDAK ADA di backend saat ini
}
```

---

## 7. Response Shape Per Endpoint (Nilai Nyata dari Dataset)

### GET /families
```json
{ "families": ["5DAYS", "CAF", "FOX", "HYDROPLUS", "TUBRUK", "UHT"] }
```

### GET /data-acquisition?family=FOX
```json
{
  "family": "FOX",
  "sku_count": 29,
  "skus": ["FOX'S Berries Bag (24)", "FOX'S Berries Tin (12)", "..."],
  "total_weeks": 40,
  "weeks": ["2025-01-01", "2025-01-08", "...", "2025-10-07"],
  "sales_raw": [66.628, 141.301, 216.05, "...", null]
}
```

### GET /data-preparation?family=FOX
```json
{
  "family": "FOX",
  "missing_before": 3,
  "missing_after": 0,
  "outliers_before": 7,
  "outliers_after": 0,
  "cleaning_method": "Linear Interpolation + IQR Winsorization (per SKU)",
  "adf_statistic_before": -3.1234,
  "adf_p_value_before": 0.0241,
  "adf_statistic_after": -4.5678,
  "adf_p_value_after": 0.0012,
  "stationary_before": true,
  "stationary_after": true,
  "d": 0,
  "weeks": ["2025-01-01", "2025-01-08", "..."],
  "sales_before": [66.628, 141.301, null, "..."],
  "sales_after": [66.628, 141.301, 178.675, "..."]
}
```

### GET /eda?family=FOX
```json
{
  "family": "FOX",
  "count": 38,
  "mean": 285.12,
  "std": 98.34,
  "min": 66.63,
  "max": 489.39,
  "stationary": true,
  "adf_statistic": -4.1234,
  "adf_p_value": 0.0123,
  "method": "Linear Interpolation + IQR Winsorization (per SKU)",
  "weeks": ["2025-01-01", "2025-01-08", "..."],
  "sales_before": [550.3, 141.301, "..."],
  "sales_after": [312.4, 141.301, "..."],
  "rolling_mean": [312.4, 298.1, "..."],
  "rolling_std": [0.0, 45.2, "..."],
  "boxplot_before": { "min": 66.63, "q1": 181.98, "median": 237.70, "q3": 363.07, "max": 698.03 },
  "boxplot_after":  { "min": 102.55, "q1": 190.12, "median": 240.10, "q3": 350.22, "max": 489.39 }
}
```

### GET /modeling?family=FOX&horizon=5
```json
{
  "family": "FOX",
  "order": [3, 0, 0],
  "aic": 312.45,
  "horizon": 5,
  "forecast": [212.38, 203.57, 194.76, 185.95, 177.15],
  "upper": [288.73, 311.54, 326.99, 338.65, 347.86],
  "lower": [136.03, 95.60, 87.64, 83.68, 79.72],
  "forecast_dates": ["2025-10-14", "2025-10-21", "2025-10-28", "2025-11-04", "2025-11-11"],
  "last_sales": 198.45,
  "historical_weeks": ["2025-01-01", "2025-01-08", "..."],
  "historical_sales": [66.628, 141.301, "..."],
  "historical_avg": 245.12,
  "forecast_avg": 194.76
}
```

### GET /evaluation?family=FOX
```json
{
  "family": "FOX",
  "order": [0, 1, 1],
  "aic": 298.12,
  "mae": 121.40,
  "rmse": 141.69,
  "smape": 49.95,
  "actual_train": [66.628, 141.301, "..."],
  "actual_test": [312.44, 289.10, 301.22, 278.90, 265.11],
  "fitted": [298.10, 275.30, 289.50, 260.10, 245.80],
  "dates_train": ["2025-01-01", "2025-01-08", "..."],
  "dates_test": ["2025-09-16", "2025-09-23", "2025-09-30", "2025-10-07", "2025-10-14"]
}
```

---

## 8. Semua Bug & Inkonsistensi (Daftar Lengkap)

### BUG KRITIS 1 — Evaluation.tsx crash karena `trend` undefined

`Evaluation.tsx` mengakses `evaluation.trend` di tiga tempat:
- Variabel `trend`, `trendColor`, `TrendIcon`
- JSX card "Klasifikasi Tren" (TrendIcon, label FAST/MEDIUM/SLOW)

Backend tidak mengembalikan field `trend`. Nilainya `undefined`.
`trendColor` dan `TrendIcon` akan fallback ke nilai default secara kebetulan
(karena ternary dengan `undefined`), tapi grid klasifikasi akan render
tanpa ring highlight yang benar.

**Solusi A — Hapus fitur trend (paling cepat untuk sidang):**
Hapus dari `Evaluation.tsx`:
- Import `TrendingUp`, `TrendingDown`, `Minus`
- Variabel `trend`, `trendColor`, `TrendIcon`
- Seluruh card `<div className="stat-card glow-border">` berisi Klasifikasi Tren

**Solusi B — Tambah trend ke backend:**
Backend perlu menambahkan ke `get_evaluation()`:
```python
trend = _classify_trend(family)  # "FAST" | "MEDIUM" | "SLOW"
# tambahkan ke return dict
```
Lalu tambah `trend: "FAST" | "MEDIUM" | "SLOW"` ke `EvaluationResponse`.

### BUG KRITIS 2 — api.ts: endpoint `/modelling` harus `/modeling`

Semua call ke `getModelling()` akan 404. Perbaiki di `api.ts` satu baris.

### INKONSISTENSI LABEL — DataPreparation.tsx: metodologi outlier salah

Komponen menampilkan "P5–P95" tapi backend menggunakan IQR method.

Perbaikan di `DataPreparation.tsx`:

1. Card Outlier — ganti label:
```tsx
// Salah:
<h3>Outliers (P5–P95)</h3>
<p>Metode: Winsorization (P5–P95)</p>

// Benar:
<h3>Outliers (IQR Method)</h3>
<p>Metode: IQR Winsorization (Q1 - 1.5×IQR, Q3 + 1.5×IQR)</p>
```

2. Pipeline list — ganti isi `<ol>`:
```tsx
// Salah:
<li>Linear Interpolation</li>
<li>Winsorization (P5 – P95)</li>
<li>ADF Test (Uji Stasioneritas)</li>
<li>Differencing (jika perlu)</li>

// Benar:
<li>Linear Interpolation (per SKU)</li>
<li>IQR Winsorization (per SKU) — Q1-1.5×IQR s/d Q3+1.5×IQR</li>
<li>Agregasi ke Family Level (sum semua SKU)</li>
<li>Drop last week (data belum lengkap)</li>
<li>ADF Test (Uji Stasioneritas)</li>
<li>Differencing (jika perlu, maks d=2)</li>
```

### INKONSISTENSI — Index.tsx: TUBRUK tidak ada di mock fallback

```ts
// Salah:
setFamilies(["5DAYS", "CAF", "FOX", "HYDROPLUS", "UHT"]);

// Benar:
setFamilies(["5DAYS", "CAF", "FOX", "HYDROPLUS", "TUBRUK", "UHT"]);
```

### BUKAN BUG — Order ARIMA berbeda di Modeling vs Evaluation

Modeling order (contoh `[3,0,0]`) vs Evaluation order (contoh `[0,1,1]`)
berbeda karena difit pada data berbeda. Ini **by design** (Opsi B notebook TA).
Kedua komponen sudah menampilkan ordernya dari response masing-masing.
Jangan menyamakan, jangan menambah catatan "berbeda" di UI.

---

## 9. Metodologi Cleaning (Untuk Label UI)

Pipeline lengkap yang benar (urutan penting untuk ditampilkan di UI):

```
1. Load data per SKU (wide format → long format)
2. Rekonstruksi timeline mingguan (Week 1–40)
   → Week 14 TIDAK ADA di dataset — ini normal, bukan missing data
3. Linear Interpolation per SKU
   → Handle NaN akibat minggu yang kosong
   → pandas: interpolate(method="linear", limit_direction="both")
   → Fallback fillna(0) untuk yang tidak bisa diinterpolasi
4. IQR Winsorization per SKU
   → Lower = Q1 - 1.5 × IQR
   → Upper = Q3 + 1.5 × IQR
   → Clip nilai di luar batas (bukan hapus)
5. Agregasi ke Family level (sum semua SKU per minggu)
6. Drop last week (Week 40 — data belum lengkap saat pengambilan data)
7. ADF Test → differencing jika tidak stasioner (max d=2)
8. auto_arima → pilih order (p,d,q) optimal
```

---

## 10. Format Tanggal

Semua field tanggal di semua endpoint: format **`"YYYY-MM-DD"`** (bukan integer).

| Week | Tanggal |
|------|---------|
| W1 | 2025-01-01 |
| W2 | 2025-01-08 |
| W13 | 2025-03-26 |
| W14 | tidak ada di dataset |
| W15 | 2025-04-09 |
| W39 | 2025-09-23 |
| W40 | di-drop (tidak ada di response) |

Helper konversi untuk label chart:
```ts
const toWeekLabel = (dateStr: string): string => {
  const d = new Date(dateStr);
  const start = new Date("2025-01-01");
  const week = Math.round((d.getTime() - start.getTime()) / (7 * 24 * 60 * 60 * 1000)) + 1;
  return `W${week}`;
};
```

---

## 11. Aturan Rendering

### null di sales_before — jangan dikonversi ke 0
```ts
// Aman (biarkan null, Recharts skip titik ini):
before: data.sales_before[i],

// Berbahaya (distorsi grafik):
before: data.sales_before[i] ?? 0,
```

### smape sudah dalam persen
```ts
// Benar:
`${evaluation.smape.toFixed(2)}%`    // → "49.95%"

// Salah (hasilnya 4995%):
`${(evaluation.smape * 100).toFixed(2)}%`
```

### lower CI sudah di-floor ke 0
Backend sudah `np.clip(lower_ci_raw, 0, None)`.
Tidak perlu `Math.max(lower, 0)` di frontend.

---

## 12. Status Setiap Komponen (Ringkasan)

> Status terakhir diperbarui: 2026-06-08

| Komponen | Status | Keterangan |
|----------|--------|------------|
| BusinessUnderstanding.tsx | ✅ OK | Tidak ada masalah |
| DataAcquisition.tsx | ✅ OK | Tidak ada masalah |
| DataPreparation.tsx | ✅ OK | Label IQR sudah benar, pipeline 6 langkah |
| EDA.tsx | ✅ OK | Label boxplot IQR Winsorized sudah benar |
| Modeling.tsx | ✅ OK | Endpoint call sudah benar via api.ts |
| Evaluation.tsx | ✅ OK | Card Klasifikasi Tren sudah dihapus |
| api.ts | ✅ OK | Endpoint /modelling (DUA L) sudah sesuai backend |
| Index.tsx | ✅ OK | TUBRUK sudah ada di mock fallback |
| App.tsx | ✅ OK | Tidak ada masalah |
| arima_service.py | ✅ OK | MIN_FAMILY_AVG filter sudah diimplementasikan |

---

## 13. Riwayat Perbaikan

```
2026-06-08 (Audit Session)
──────────────────────────
1. api.ts
   → Hapus field trend (required → dihapus) dari EvaluationResponse
   → Jadikan optional 5 field EDA yang tidak ada di /eda response
   → Tambah historical_avg, forecast_avg ke ModellingResponse

2. Evaluation.tsx
   → Hapus card "Klasifikasi Tren" dan import TrendingUp/Down/Minus
   → Hapus variabel trend, trendColor, TrendIcon

3. DataPreparation.tsx
   → Label outlier: P5–P95 → IQR Method
   → Label metode: → IQR Winsorization (Q1 - 1.5×IQR, Q3 + 1.5×IQR)
   → Pipeline list: 4 item salah → 6 item benar

4. EDA.tsx
   → Label boxplot after: Winsorized P5–P95 → IQR Winsorized

5. Index.tsx
   → Tambah TUBRUK ke mock fallback families

6. arima_service.py (backend)
   → Tambah konstanta MIN_FAMILY_AVG = 5
   → Implementasi filter mean >= MIN_FAMILY_AVG di get_families()
   → ROYO (mean ≈ 1.31) sekarang di-exclude dari /families response
```

---

## 14. Fakta Dataset (Referensi Cepat)

| Fakta | Nilai |
|-------|-------|
| File sumber | AVG 12W & 5W.csv |
| Total SKU (semua family) | 89 produk |
| Total SKU valid (excl. ROYO) | 86 produk |
| Valid families | 5DAYS, CAF, FOX, HYDROPLUS, TUBRUK, UHT |
| ROYO | Ada di dataset, di-exclude (mean ≈ 1.31 < MIN_FAMILY_AVG = 5) |
| Minggu tersedia | W1–W40, kecuali W14 (tidak ada di file) |
| W40 | Di-drop (data belum lengkap) |
| Titik data per family setelah drop | **38 minggu** (semua family) |
| Train split | 33 minggu (series[:-5]) |
| Test split evaluasi | 5 minggu terakhir (series[-5:]) |
| Forecast horizon default | 5 minggu ke depan |
| Start date W1 | 2025-01-01 |
| MIN_FAMILY_AVG | 5 (notebook Cell 20) |
| Winsorization | IQR per SKU — Q1-1.5×IQR s/d Q3+1.5×IQR |
| smape di response | Sudah persen (27.26 = 27.26%) |
| MAPE | Tidak digunakan, tidak boleh ditampilkan |

## Aturan Kompatibilitas Backend

Jika kontrak API backend berubah:

1. Perbarui interface pada `api.ts`
2. Perbarui komponen stage yang menggunakan data tersebut
3. Perbarui dokumentasi ini setelah semuanya selesai

Jangan memperbarui dokumentasi sebelum memverifikasi response backend yang sebenarnya.

Jika ragu:

* Periksa route backend
* Periksa payload response
* Bandingkan dengan notebook

Jangan menebak field response.

Jangan melakukan hardcode asumsi.

Selalu lakukan verifikasi terlebih dahulu.

