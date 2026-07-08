// src/components/stages/DataPreparation.tsx
import { useEffect, useState } from "react";
import {
  CheckCircle2, AlertTriangle, Beaker, ArrowDownUp, Loader2
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { getDataPreparation, getCleaningSamples, type DataPreparationResponse, type CleaningSamplesResponse } from "@/services/api";

interface Props {
  family: string;
}

const DataPreparation = ({ family }: Props) => {
  const [data, setData] = useState<DataPreparationResponse | null>(null);
  const [samples, setSamples] = useState<CleaningSamplesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [prepRes, samplesRes] = await Promise.all([
          getDataPreparation(family),
          getCleaningSamples(family)
        ]);
        if (!cancelled) {
          setData(prepRes);
          setSamples(samplesRes);
        }
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Gagal memuat data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [family]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm py-8">
        <Loader2 className="w-4 h-4 animate-spin" /> Memuat hasil preparation…
      </div>
    );
  }

  if (error || !data) {
    return <p className="text-sm text-destructive py-4">{error ?? "Data tidak tersedia"}</p>;
  }

  const chartData = data.weeks.map((w, i) => ({
    week: w,
    before: data.sales_before[i],
    after: data.sales_after[i],
  }));

  const tooltipStyle = {
    contentStyle: {
      background: "hsl(220 22% 13%)",
      border: "1px solid hsl(220 18% 20%)",
      borderRadius: 8,
      color: "hsl(210 20% 92%)",
    },
  };
  const tickStyle = { fontSize: 10, fill: "hsl(215 15% 55%)" };
  const gridStyle = { strokeDasharray: "3 3", stroke: "hsl(220 18% 20%)" };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 3</span>
        <h2 className="section-header mt-3">Data Preparation &amp; Cleaning</h2>
        <p className="text-muted-foreground mt-1">
          Membersihkan data dari missing values dan outlier, kemudian menguji stasioneritas.
        </p>
      </div>

      {/* Cleaning Method */}
      <div className="stat-card glow-border">
        <h3 className="text-sm font-semibold text-primary mb-2 flex items-center gap-2">
          <Beaker className="w-4 h-4" /> Pipeline Cleaning
        </h3>
        <ol className="text-sm text-secondary-foreground space-y-1 list-decimal list-inside">
          <li>Linear Interpolation (per SKU)</li>
          <li>IQR Winsorization (per SKU) — Q1-1.5×IQR s/d Q3+1.5×IQR</li>
          <li>Agregasi ke Family Level (sum semua SKU)</li>
          <li>Drop last week (data belum lengkap)</li>
          <li>ADF Test (Uji Stasioneritas)</li>
          <li>Differencing (jika perlu, maks d=2)</li>
        </ol>
        <p className="text-xs text-muted-foreground mt-2 font-mono">
          {data.cleaning_method}
        </p>
      </div>

      {/* Missing Values & Outliers Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" /> Missing Values
          </h3>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-destructive">{data.missing_before}</div>
              <div className="text-xs text-muted-foreground">Sebelum</div>
            </div>
            <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
            <div className="text-center">
              <div className="text-2xl font-bold text-success">{data.missing_after}</div>
              <div className="text-xs text-muted-foreground">Sesudah</div>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">Metode: Linear Interpolation</p>
        </div>

        <div className="stat-card">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" /> Outliers (IQR Method)
          </h3>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-destructive">{data.outliers_before}</div>
              <div className="text-xs text-muted-foreground">Sebelum</div>
            </div>
            <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
            <div className="text-center">
              <div className="text-2xl font-bold text-success">{data.outliers_after}</div>
              <div className="text-xs text-muted-foreground">Sesudah</div>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">Metode: IQR Winsorization</p>
        </div>
      </div>

      {/* ----- TRANSPARANSI DATA CLEANING ----- */}
      {samples && (
        <div className="space-y-4">
          {/* 1. Missing Values Examples */}
          <div className="stat-card">
            <h3 className="text-sm font-semibold text-primary flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4" /> 
              Detail Missing Values (Total: {samples.total_missing_before})
            </h3>
            <div className="space-y-4">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">📌 Sebelum Interpolasi (NULL asli)</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="border-b border-secondary">
                        <tr><th className="text-left py-1">Produk</th><th className="text-left py-1">Minggu</th><th className="text-right py-1">Sales</th></tr>
                      </thead>
                      <tbody>
                        {samples.missing_before_samples.map((item, idx) => (
                          <tr key={idx} className="border-b border-secondary/50">
                            <td className="py-1 text-xs">{item.Product}</td>
                            <td className="py-1 text-xs">W{item.Week}</td>
                            <td className="py-1 text-right font-mono text-destructive">NULL</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Menampilkan {samples.missing_before_samples.length} dari {samples.total_missing_before} missing values.</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">✅ Setelah Interpolasi (Nilai terisi)</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="border-b border-secondary">
                        <tr><th className="text-left py-1">Produk</th><th className="text-left py-1">Minggu</th><th className="text-right py-1">Sales</th></tr>
                      </thead>
                      <tbody>
                        {samples.missing_after_samples.map((item, idx) => (
                          <tr key={idx} className="border-b border-secondary/50">
                            <td className="py-1 text-xs">{item.Product}</td>
                            <td className="py-1 text-xs">W{item.Week}</td>
                            <td className="py-1 text-right font-mono text-success">{item.Sales?.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Semua missing values berhasil diinterpolasi (sisa = {samples.total_missing_after}).</p>
                </div>
            </div>
          </div>

          {/* Placeholder Gambar - Missing Values */}
          <div className="stat-card border-dashed border-2 border-secondary flex flex-col items-center justify-center gap-2 py-8 text-muted-foreground">
            <p className="text-xs font-medium">Gambar Arsitektur Linear Interpolation</p>
            <img src="./images/Linear Interpolation Architecture.jpeg" alt="linearinterpolation" />
          </div>

          {/* 2. Outliers Examples */}
          <div className="stat-card">
            <h3 className="text-sm font-semibold text-primary flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4" /> 
              Detail Outliers (Total: {samples.total_outliers_before})
            </h3>
            {samples.outliers_before_samples.length > 0 && (
              <div className="space-y-4">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">📌 Sebelum Winsorization (Nilai Outlier)</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="border-b border-secondary">
                        <tr><th className="text-left py-1">Produk</th><th className="text-left py-1">Minggu</th><th className="text-right py-1">Sales</th></tr>
                      </thead>
                      <tbody>
                        {samples.outliers_before_samples.map((item, idx) => (
                          <tr key={idx} className="border-b border-secondary/50">
                            <td className="py-1 text-xs">{item.Product}</td>
                            <td className="py-1 text-xs">W{item.Week}</td>
                            <td className="py-1 text-right font-mono text-warning">{item.Sales?.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">✅ Setelah Winsorization (Nilai Terkoreksi)</p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="border-b border-secondary">
                        <tr><th className="text-left py-1">Produk</th><th className="text-left py-1">Minggu</th><th className="text-right py-1">Sales</th></tr>
                      </thead>
                      <tbody>
                        {samples.outliers_after_samples.map((item, idx) => (
                          <tr key={idx} className="border-b border-secondary/50">
                            <td className="py-1 text-xs">{item.Product}</td>
                            <td className="py-1 text-xs">W{item.Week}</td>
                            <td className="py-1 text-right font-mono text-success">{item.Sales?.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Outlier berhasil di-winsorize (sisa outlier setelah = {samples.total_outliers_after}).</p>
                </div>
              </div>
            )}
          </div>

          {/* Placeholder Gambar - Outliers */}
        <div className="stat-card border-dashed border-2 border-secondary flex flex-col items-center justify-center gap-2 py-8 text-muted-foreground">
          <p className="text-xs font-medium">Gambar Aristektur Winsorization</p>
          <img src="./images/Winsorization.jpeg" alt="winsorization" />
        </div>

      {/* Before vs After Chart */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">📊 Sales Before vs After Cleaning</h3>
        <ResponsiveContainer width="100%" height={230}>
          <LineChart data={chartData}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="week" tick={tickStyle} interval={4} />
            <YAxis tick={tickStyle} />
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="before" stroke="hsl(35 92% 60%)" dot={false} name="Sebelum Cleaning" strokeWidth={1.5} />
            <Line type="monotone" dataKey="after" stroke="hsl(174 72% 50%)" dot={false} name="Setelah Cleaning" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

          {/* 3. Preview Data Family (5 minggu pertama) */}
          <div className="stat-card">
            <h3 className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
              📋 Preview Data Family (5 minggu pertama)
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-secondary">
                  <tr>
                    <th className="text-left py-1">Minggu</th>
                    <th className="text-right py-1">Total Sales (Sebelum Cleaning)</th>
                    <th className="text-right py-1">Total Sales (Setelah Cleaning)</th>
                  </tr>
                </thead>
                <tbody>
                  {samples.sales_preview.map((item, idx) => (
                    <tr key={idx} className="border-b border-secondary/50">
                      <td className="py-1 text-xs">{item.week}</td>
                      <td className="py-1 text-right font-mono">{item.sales_before.toFixed(2)}</td>
                      <td className="py-1 text-right font-mono">{item.sales_after.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground mt-2">Menampilkan 5 minggu pertama dari total {data.weeks.length} minggu.</p>
          </div>
        </div>
      )}

      {/* ADF Test */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" /> Augmented Dickey-Fuller Test
        </h3>
        <div className="grid grid-cols-2 gap-4 mb-3">
          <div className="p-3 rounded bg-secondary/30">
            <p className="text-xs text-muted-foreground mb-2 font-semibold">Sebelum Differencing</p>
            <div className="space-y-1">
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">ADF Stat</span><span className="font-mono">{data.adf_statistic_before}</span></div>
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">p-value</span><span className={`font-mono ${data.adf_p_value_before < 0.05 ? "text-success" : "text-warning"}`}>{data.adf_p_value_before}</span></div>
              <div className={`text-xs font-medium mt-1 ${data.stationary_before ? "text-success" : "text-warning"}`}>{data.stationary_before ? "✓ Stasioner" : "⚠ Tidak Stasioner"}</div>
            </div>
          </div>
          <div className="p-3 rounded bg-secondary/30">
            <p className="text-xs text-muted-foreground mb-2 font-semibold">Setelah Differencing (d={data.d})</p>
            <div className="space-y-1">
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">ADF Stat</span><span className="font-mono">{data.adf_statistic_after}</span></div>
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">p-value</span><span className={`font-mono ${data.adf_p_value_after < 0.05 ? "text-success" : "text-warning"}`}>{data.adf_p_value_after}</span></div>
              <div className={`text-xs font-medium mt-1 ${data.stationary_after ? "text-success" : "text-warning"}`}>{data.stationary_after ? "✓ Stasioner" : "⚠ Tidak Stasioner"}</div>
            </div>
          </div>
        </div>
        <div className={`p-2 rounded text-xs font-medium text-center ${data.stationary_after ? "bg-success/10 text-success" : "bg-warning/10 text-warning"}`}>
          {data.d === 0 ? "✓ Data sudah stasioner — tidak perlu differencing" : `✓ Data stasioner setelah differencing orde d=${data.d}`}
        </div>
      </div>
    </div>
  );
};

export default DataPreparation;