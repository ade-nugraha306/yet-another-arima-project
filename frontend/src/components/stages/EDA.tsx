import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, ReferenceLine, ComposedChart, Legend,
} from "recharts";
import { getEDA, type EDAResponse, type BoxplotStats } from "@/services/api";

interface Props {
  family: string;
}

function BoxplotViz({ stats, label, color }: { stats: BoxplotStats; label: string; color: string }) {
  const range = stats.max - stats.min || 1;
  const pct = (v: number) => ((v - stats.min) / range) * 100;
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold text-muted-foreground mb-2">{label}</p>
      <div className="relative h-8 bg-secondary/30 rounded">
        <div
          className="absolute h-full rounded"
          style={{ left: `${pct(stats.q1)}%`, width: `${pct(stats.q3) - pct(stats.q1)}%`, background: color, opacity: 0.6 }}
        />
        <div className="absolute h-full w-0.5 bg-white" style={{ left: `${pct(stats.median)}%` }} />
        <div className="absolute top-1/2 -translate-y-1/2 h-0.5 bg-muted-foreground" style={{ left: `${pct(stats.min)}%`, width: `${pct(stats.q1) - pct(stats.min)}%` }} />
        <div className="absolute top-1/2 -translate-y-1/2 h-0.5 bg-muted-foreground" style={{ left: `${pct(stats.q3)}%`, width: `${pct(stats.max) - pct(stats.q3)}%` }} />
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground font-mono mt-1">
        <span>{stats.min.toFixed(0)}</span><span>Q1:{stats.q1.toFixed(0)}</span><span>Med:{stats.median.toFixed(0)}</span><span>Q3:{stats.q3.toFixed(0)}</span><span>{stats.max.toFixed(0)}</span>
      </div>
    </div>
  );
}

const EDA = ({ family }: Props) => {
  const [eda, setEda] = useState<EDAResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);


  useEffect(() => {
    if (!family) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getEDA(family);
        if (!cancelled) setEda(data);
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Gagal memuat EDA");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [family]);

  if (loading) return <div className="flex items-center gap-2 text-muted-foreground text-sm py-8"><Loader2 className="w-4 h-4 animate-spin" /> Memuat EDA…</div>;
  if (error || !eda) return <p className="text-sm text-destructive py-4">{error ?? "Data tidak tersedia"}</p>;

  const salesBefore = eda.sales_before;
  const salesAfter = eda.sales_after;
  const weeks = eda.weeks;
  const trendData = weeks.map((w, i) => ({ week: w, before: salesBefore[i], after: salesAfter[i] }));

  const histBefore = eda.distribution_before || [];
  const histAfter = eda.distribution_after || [];
  const acfBefore = eda.acf_before || [];
  const acfAfter = eda.acf_after || [];
  const pacfBefore = eda.pacf_before || [];
  const pacfAfter = eda.pacf_after || [];
  const boxBeforeSum = eda.boxplot_before_summary;
  const boxAfterSum = eda.boxplot_after_summary;

  const n = salesAfter.length;
  const ci = 1.96 / Math.sqrt(n);

  const rollingWindow = 4;
  const computeRollingMean = (arr: number[], window: number) => {
    return arr.map((_, idx) => {
      const start = Math.max(0, idx - window + 1);
      const slice = arr.slice(start, idx + 1);
      return slice.reduce((a, b) => a + b, 0) / slice.length;
    });
  };
  const computeRollingStd = (arr: number[], window: number) => {
    return arr.map((_, idx) => {
      const start = Math.max(0, idx - window + 1);
      const slice = arr.slice(start, idx + 1);
      const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
      const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / slice.length;
      return Math.sqrt(variance);
    });
  };
  const rollingMeanBefore = computeRollingMean(salesBefore, rollingWindow);
  const rollingStdBefore = computeRollingStd(salesBefore, rollingWindow);
  const rollingMeanAfter = eda.rolling_mean ?? computeRollingMean(salesAfter, rollingWindow);
  const rollingStdAfter = eda.rolling_std ?? computeRollingStd(salesAfter, rollingWindow);
  const rollingData = weeks.map((w, i) => ({
    week: w,
    before: salesBefore[i],
    after: salesAfter[i],
    rollingMeanBefore: rollingMeanBefore[i],
    rollingStdBefore: rollingStdBefore[i],
    rollingMeanAfter: rollingMeanAfter[i],
    rollingStdAfter: rollingStdAfter[i],
  }));

  const previewData = trendData.slice(0, 5);

  const tooltipStyle = { contentStyle: { background: "hsl(220 22% 13%)", border: "1px solid hsl(220 18% 20%)", borderRadius: 8, color: "hsl(210 20% 92%)" } };
  const gridStyle = { strokeDasharray: "3 3", stroke: "hsl(220 18% 20%)" };
  const tickStyle = { fontSize: 10, fill: "hsl(215 15% 55%)" };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 4</span>
        <h2 className="section-header mt-3">Exploratory Data Analysis</h2>
        <p className="text-muted-foreground mt-1">Mengeksplorasi pola, tren, dan distribusi data penjualan family <span className="text-primary font-semibold">{family}</span>.</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Mean", value: eda.mean.toFixed(2) },
          { label: "Std Dev", value: eda.std.toFixed(2) },
          { label: "Min", value: eda.min.toFixed(2) },
          { label: "Max", value: eda.max.toFixed(2) },
        ].map(s => (
          <div key={s.label} className="stat-card text-center">
            <div className="text-xs text-muted-foreground mb-1">{s.label}</div>
            <div className="text-2xl font-bold font-mono text-primary">{s.value}</div>
          </div>
        ))}
      </div>

      {/* 1. Weekly Sales Trend */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-2">📈 Weekly Sales Trend — Before vs After Cleaning</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={trendData}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="week" tick={tickStyle} interval={4} />
            <YAxis tick={tickStyle} />
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="before" stroke="hsl(35 92% 60%)" strokeWidth={1.5} dot={false} name="Sebelum Cleaning" />
            <Line type="monotone" dataKey="after"  stroke="hsl(174 72% 50%)" strokeWidth={2} dot={false} name="Setelah Cleaning" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Preview Data Family (5 minggu pertama) */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">📋 Preview Data Family (5 minggu pertama)</h3>
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
              {previewData.map((item, idx) => (
                <tr key={idx} className="border-b border-secondary/50">
                  <td className="py-1 text-xs">{item.week}</td>
                  <td className="py-1 text-right font-mono">{item.before.toFixed(2)}</td>
                  <td className="py-1 text-right font-mono">{item.after.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Menampilkan 5 minggu pertama dari total {eda.weeks.length} minggu.
        </p>
      </div>

      {/* 2. Distribusi (Histogram) — Before vs After */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-2">📊 Distribusi — Sebelum Cleaning</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={histBefore}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="range" tick={tickStyle} />
              <YAxis tick={tickStyle} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="count" fill="hsl(35 92% 60%)" name="Frekuensi" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-2">📊 Distribusi — Setelah Cleaning</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={histAfter}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="range" tick={tickStyle} />
              <YAxis tick={tickStyle} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="count" fill="hsl(174 72% 50%)" name="Frekuensi" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tabel distribusi */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">📋 Data Distribusi (Range & Frekuensi)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="border-b border-secondary">
              <tr><th className="text-left py-1">Range Sales</th><th className="text-right py-1">Frekuensi (Before)</th><th className="text-right py-1">Frekuensi (After)</th></tr>
            </thead>
            <tbody>
              {histBefore.map((item, idx) => {
                const afterItem = histAfter[idx] || { count: 0 };
                return (
                  <tr key={idx} className="border-b border-secondary/50">
                    <td className="py-1 font-mono">{item.range}</td>
                    <td className="py-1 text-right font-mono">{item.count}</td>
                    <td className="py-1 text-right font-mono">{afterItem.count}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. ACF */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-2">📈 ACF — Sebelum Cleaning</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={acfBefore}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="lag" tick={tickStyle} />
              <YAxis domain={[-1, 1]} tick={tickStyle} />
              <Tooltip {...tooltipStyle} />
              <ReferenceLine y={ci} stroke="hsl(0 70% 60%)" strokeDasharray="5 5" />
              <ReferenceLine y={-ci} stroke="hsl(0 70% 60%)" strokeDasharray="5 5" />
              <Bar dataKey="value" fill="hsl(35 92% 60%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-2">📈 ACF — Setelah Cleaning</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={acfAfter}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="lag" tick={tickStyle} />
              <YAxis domain={[-1, 1]} tick={tickStyle} />
              <Tooltip {...tooltipStyle} />
              <ReferenceLine y={ci} stroke="hsl(0 70% 60%)" strokeDasharray="5 5" />
              <ReferenceLine y={-ci} stroke="hsl(0 70% 60%)" strokeDasharray="5 5" />
              <Bar dataKey="value" fill="hsl(174 72% 50%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tabel ACF */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">📋 Tabel Nilai ACF</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="border-b border-secondary">
              <tr><th className="text-left py-1">Lag</th><th className="text-right py-1">ACF (Before)</th><th className="text-right py-1">ACF (After)</th></tr>
            </thead>
            <tbody>
              {acfBefore.map((item, idx) => {
                const afterItem = acfAfter[idx] || { value: 0 };
                return (
                  <tr key={idx} className="border-b border-secondary/50">
                    <td className="py-1 font-mono">{item.lag}</td>
                    <td className="py-1 text-right font-mono">{item.value.toFixed(4)}</td>
                    <td className="py-1 text-right font-mono">{afterItem.value.toFixed(4)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. PACF */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-2">📉 PACF — Sebelum Cleaning</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pacfBefore}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="lag" tick={tickStyle} />
              <YAxis domain={[-1, 1]} tick={tickStyle} />
              <Tooltip {...tooltipStyle} />
              <ReferenceLine y={ci} stroke="hsl(0 70% 60%)" strokeDasharray="5 5" />
              <ReferenceLine y={-ci} stroke="hsl(0 70% 60%)" strokeDasharray="5 5" />
              <Bar dataKey="value" fill="hsl(35 92% 60%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-2">📉 PACF — Setelah Cleaning</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={pacfAfter}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="lag" tick={tickStyle} />
              <YAxis domain={[-1, 1]} tick={tickStyle} />
              <Tooltip {...tooltipStyle} />
              <ReferenceLine y={ci} stroke="hsl(0 70% 60%)" strokeDasharray="5 5" />
              <ReferenceLine y={-ci} stroke="hsl(0 70% 60%)" strokeDasharray="5 5" />
              <Bar dataKey="value" fill="hsl(174 72% 50%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tabel PACF */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">📋 Tabel Nilai PACF</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="border-b border-secondary">
              <tr><th className="text-left py-1">Lag</th><th className="text-right py-1">PACF (Before)</th><th className="text-right py-1">PACF (After)</th></tr>
            </thead>
            <tbody>
              {pacfBefore.map((item, idx) => {
                const afterItem = pacfAfter[idx] || { value: 0 };
                return (
                  <tr key={idx} className="border-b border-secondary/50">
                    <td className="py-1 font-mono">{item.lag}</td>
                    <td className="py-1 text-right font-mono">{item.value.toFixed(4)}</td>
                    <td className="py-1 text-right font-mono">{afterItem.value.toFixed(4)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Boxplots */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-4">📦 Boxplot — Before vs After Cleaning</h3>
        <div className="space-y-5">
          <BoxplotViz stats={eda.boxplot_before} label="Sebelum Cleaning" color="hsl(35 92% 60%)" />
          <BoxplotViz stats={eda.boxplot_after}  label="Setelah Cleaning (IQR Winsorized)" color="hsl(174 72% 50%)" />
        </div>
      </div>

      {/* Tabel ringkasan boxplot */}
      {boxBeforeSum && boxAfterSum && (
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-3">📋 Ringkasan Statistik Boxplot</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="border-b border-secondary">
                <tr><th className="text-left py-1">Statistik</th><th className="text-right py-1">Sebelum Cleaning</th><th className="text-right py-1">Setelah Cleaning</th></tr>
              </thead>
              <tbody>
                <tr className="border-b border-secondary/50"><td className="py-1">Min</td><td className="text-right font-mono">{boxBeforeSum.min}</td><td className="text-right font-mono">{boxAfterSum.min}</td></tr>
                <tr className="border-b border-secondary/50"><td className="py-1">Q1</td><td className="text-right font-mono">{boxBeforeSum.q1}</td><td className="text-right font-mono">{boxAfterSum.q1}</td></tr>
                <tr className="border-b border-secondary/50"><td className="py-1">Median</td><td className="text-right font-mono">{boxBeforeSum.median}</td><td className="text-right font-mono">{boxAfterSum.median}</td></tr>
                <tr className="border-b border-secondary/50"><td className="py-1">Q3</td><td className="text-right font-mono">{boxBeforeSum.q3}</td><td className="text-right font-mono">{boxAfterSum.q3}</td></tr>
                <tr className="border-b border-secondary/50"><td className="py-1">Max</td><td className="text-right font-mono">{boxBeforeSum.max}</td><td className="text-right font-mono">{boxAfterSum.max}</td></tr>
                <tr className="border-b border-secondary/50"><td className="py-1">IQR</td><td className="text-right font-mono">{boxBeforeSum.iqr}</td><td className="text-right font-mono">{boxAfterSum.iqr}</td></tr>
                <tr className="border-b border-secondary/50"><td className="py-1">Outlier Count</td><td className="text-right font-mono">{boxBeforeSum.outlier_count}</td><td className="text-right font-mono">{boxAfterSum.outlier_count}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 6. Rolling Mean & Std */}
      {/* <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-2">📊 Rolling Mean & Std (4 Minggu) — Before vs After</h3>
        <ResponsiveContainer width="100%" height={250}>
          <ComposedChart data={rollingData}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="week" tick={tickStyle} interval={4} />
            <YAxis tick={tickStyle} />
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line dataKey="rollingMeanBefore" stroke="hsl(35 92% 60%)" strokeWidth={1.5} dot={false} name="Rolling Mean (Before)" />
            <Line dataKey="rollingStdBefore" stroke="hsl(35 92% 60%)" strokeDasharray="4 4" dot={false} name="Rolling Std (Before)" />
            <Line dataKey="rollingMeanAfter" stroke="hsl(174 72% 50%)" strokeWidth={2} dot={false} name="Rolling Mean (After)" />
            <Line dataKey="rollingStdAfter" stroke="hsl(174 72% 50%)" strokeDasharray="4 4" dot={false} name="Rolling Std (After)" />
          </ComposedChart>
        </ResponsiveContainer>
      </div> */}
    </div>
  );
};

export default EDA;