# Tahapan Preprocessing Data — Project Forecasting Penjualan

## 1. Tujuan
Proses ini bertujuan untuk **membersihkan dan menyiapkan data penjualan mingguan** agar dapat digunakan untuk **analisis deret waktu (time series)** dan pemodelan seperti **ARIMA atau Machine Learning Regression**.

---

## 2. Dataset
- **Sumber**: File Excel `AVG 12W & 5W (W1–W40).csv`
- **Struktur awal**: Data penjualan disajikan secara _wide format_, dengan kolom minggu (W1, W2, dst.)
- **Kolom penting**:
  - `PRINC 1` — Prinsipal produk  
  - `Kode Produk` — Kode unik per produk  
  - `Produk` — Nama produk  
  - `Week` — Nomor minggu (1–40)  
  - `Sales` — Jumlah penjualan  

---

## 3. Langkah-Langkah Preprocessing

### 3.1 Load dan Agregasi Data
File Excel dibaca dua kali:  
- Pertama untuk menemukan baris header dinamis (“Kode Produk”)  
- Kedua untuk memuat ulang dengan header yang benar.

Data kemudian diubah dari **wide format → long format** menggunakan fungsi `pd.melt`,  
sehingga setiap baris merepresentasikan kombinasi `(Produk, Week, Sales)`.

Ditambahkan kolom **Date** berdasarkan minggu ke-1 (dengan asumsi mulai 1 Januari 2024).

---

### 3.2 Data Cleaning
Langkah pembersihan meliputi:

| Permasalahan | Solusi yang Diterapkan |
|---------------|------------------------|
| Missing value (`NaN`) | Diisi menggunakan interpolasi linear |
| Nilai negatif | Diganti menjadi `0` |
| Nilai `0` yang tidak signifikan (kurang dari 30%) | Diganti dengan median rolling window (3 minggu) |
| Outlier | Dideteksi menggunakan **IQR (Interquartile Range)** dan diklip antara batas bawah dan atas |

---

### 3.3 Pembuatan Fitur Time Series
Menambahkan fitur pendukung pola musiman:

| Fitur | Deskripsi |
|-------|------------|
| `Week_Number` | Urutan minggu ke-n untuk setiap produk |
| `Month`, `Quarter` | Informasi bulan dan kuartal |
| `MA_4`, `MA_8` | Rata-rata bergerak (4 dan 8 minggu) |
| `STD_4` | Deviasi standar 4 minggu terakhir |

---

### 3.4 Uji Stasioneritas
Data diuji menggunakan **Augmented Dickey-Fuller (ADF Test)**:
- Jika p-value ≤ 0.05 → data **stasioner**
- Jika tidak → dilakukan **differencing** hingga stasioner
- Nilai **d (differencing order)** disimpan untuk parameter model ARIMA

---

### 3.5 Visualisasi Hasil
Menampilkan beberapa grafik diagnostik:
1. **Plot Tren Mingguan** — visualisasi pola naik-turun penjualan  
2. **Histogram & Q-Q Plot** — pemeriksaan distribusi  
3. **Boxplot** — deteksi outlier  
4. **Rolling Mean & STD** — melihat kestabilan mean/varian  
5. **ACF Plot** — melihat autokorelasi antar minggu  

---

## 4. Hasil Akhir

Setelah preprocessing, diperoleh data yang:

Bebas dari missing value & nilai ekstrim  
Siap digunakan untuk pemodelan **ARIMA / LSTM / Regression**  
Memiliki kolom waktu (`Date`) dan fitur musiman tambahan  

Contoh hasil akhir (`head()`):

| Date       | Produk                    | Sales | MA_4 | STD_4 | Quarter |
|-------------|---------------------------|--------|-------|--------|----------|
| 2024-01-01 | FOX'S Fruits Tin (12) SS | 0.75   | 0.75  | 0.00   | 1 |
| 2024-01-08 | FOX'S Fruits Tin (12) SS | 0.75   | 0.75  | 0.00   | 1 |
| 2024-01-15 | FOX'S Fruits Tin (12) SS | 0.00   | 0.50  | 0.43   | 1 |

---

## 5. Kesimpulan
Tahapan preprocessing ini menghasilkan dataset bersih dan terstruktur,  
sehingga dapat langsung digunakan untuk tahap **modeling dan evaluasi prediksi penjualan mingguan.**

---

## 6. Referensi
- Hyndman, R.J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice (3rd ed.)*  
- Documentation: [pandas](https://pandas.pydata.org/), [statsmodels](https://www.statsmodels.org/), [matplotlib](https://matplotlib.org/)

---
