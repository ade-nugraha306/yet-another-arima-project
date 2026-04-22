import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, ReferenceLine, ComposedChart,
} from "recharts";
import { getEDA, type EDAResponse, type SeasonalityCell } from "@/services/api";

interface Props {
  product: string;
}

// ── ACF ─────────────────────────────────────────────
function computeACF(values: number[], maxLag: number) {
  const n = values.length;
  const mean = values.reduce((a, b) => a + b, 0) / n;
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / n;

  // ❗ Handle variance = 0
  if (variance === 0) {
    return Array.from({ length: maxLag + 1 }, (_, lag) => ({
      lag,
      acf: lag === 0 ? 1 : 0,
      upper: 0,
      lower: 0,
    }));
  }

  const ci = 1.96 / Math.sqrt(n);
  const result = [];

  for (let lag = 0; lag <= maxLag; lag++) {
    let cov = 0;
    for (let i = lag; i < n; i++) {
      cov += (values[i] - mean) * (values[i - lag] - mean);
    }
    result.push({
      lag,
      acf: lag === 0 ? 1 : (cov / n) / variance,
      upper: ci,
      lower: -ci,
    });
  }

  return result;
}

// ── PACF (approx) ───────────────────────────────────
function computePACF(values: number[], maxLag: number) {
  const acf = computeACF(values, maxLag);
  const n = values.length;
  const ci = 1.96 / Math.sqrt(n);

  const pacf: { lag: number; pacf: number; upper: number; lower: number }[] = [];

  for (let k = 0; k <= maxLag; k++) {
    if (k === 0) {
      pacf.push({ lag: 0, pacf: 1, upper: ci, lower: -ci });
      continue;
    }
    if (k === 1) {
      pacf.push({ lag: 1, pacf: acf[1].acf, upper: ci, lower: -ci });
      continue;
    }

    const phi: number[] = new Array(k).fill(0);
    phi[0] = acf[1].acf;

    for (let j = 2; j <= k; j++) {
      let num = acf[j].acf;
      for (let i = 1; i < j; i++) num -= phi[i - 1] * acf[j - i].acf;

      let den = 1;
      for (let i = 1; i < j; i++) den -= phi[i - 1] * acf[i].acf;

      const newPhi = num / den;
      const prevPhi = [...phi];

      for (let i = 0; i < j - 1; i++) {
        phi[i] = prevPhi[i] - newPhi * prevPhi[j - 2 - i];
      }

      phi[j - 1] = newPhi;
    }

    pacf.push({ lag: k, pacf: phi[k - 1], upper: ci, lower: -ci });
  }

  return pacf;
}

// ── SEASONALITY HEATMAP ─────────────────────────────
const WEEK_COLS = ["W1", "W2", "W3", "W4"] as const;

function SeasonalityHeatmap({ data }: { data: SeasonalityCell[] }) {
  // Build lookup: month+week_in_month → avg_sales
  const lookup = new Map<string, number>();
  data.forEach(d => lookup.set(`${d.month}-${d.week_in_month}`, d.avg_sales));

  // Preserve month order as they appear (backend returns sorted by month_num)
  const months = [...new Set(data.map(d => d.month))];

  // Min/max for intensity scaling
  const values = data.map(d => d.avg_sales);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  return (
    <div className="stat-card">
      <h3 className="text-sm font-semibold text-primary mb-3">🌡️ Seasonality Heatmap</h3>
      <p className="text-xs text-muted-foreground mb-3">
        Rata-rata penjualan per minggu dalam bulan — warna lebih terang = lebih tinggi.
      </p>
      <div className="overflow-x-auto">
        <div
          className="inline-grid gap-1"
          style={{ gridTemplateColumns: `64px repeat(4, minmax(56px, 1fr))` }}
        >
          {/* Header row */}
          <div />
          {WEEK_COLS.map(w => (
            <div key={w} className="text-xs text-muted-foreground text-center font-mono py-1">
              {w}
            </div>
          ))}

          {/* Data rows */}
          {months.map(month => (
            <>
              <div key={month} className="text-xs text-muted-foreground font-mono py-2 flex items-center">
                {month}
              </div>
              {WEEK_COLS.map(wk => {
                const val = lookup.get(`${month}-${wk}`);
                if (val === undefined) {
                  return (
                    <div
                      key={wk}
                      className="rounded text-xs text-center p-2 font-mono text-muted-foreground"
                      style={{ background: "hsl(220 18% 15%)" }}
                    >
                      —
                    </div>
                  );
                }
                const intensity = (val - minVal) / range;
                return (
                  <div
                    key={wk}
                    className="rounded text-xs text-center p-2 font-mono font-semibold"
                    style={{
                      background: `hsl(174 72% ${15 + intensity * 40}%)`,
                      color: intensity > 0.55 ? "hsl(220 25% 10%)" : "hsl(210 20% 88%)",
                    }}
                    title={`${month} ${wk}: ${val}`}
                  >
                    {val.toFixed(0)}
                  </div>
                );
              })}
            </>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── COMPONENT ───────────────────────────────────────
const EDA = ({ product }: Props) => {
  const [eda, setEda] = useState<EDAResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const data = await getEDA(product);
        if (!cancelled) setEda(data);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Gagal memuat EDA");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true };
  }, [product]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm py-8">
        <Loader2 className="w-4 h-4 animate-spin" /> Memuat EDA…
      </div>
    );
  }

  if (error || !eda) {
    return <p className="text-sm text-destructive py-4">{error ?? "Data tidak tersedia"}</p>;
  }

  // ── DATA ──────────────────────────────────────────

  const timeSeriesData = eda.dates.map((d, i) => ({
    week: d,
    sales: eda.sales[i],
    rollingMean: eda.rolling_mean?.[i],
    rollingStd: eda.rolling_std?.[i],
  }));

  // Histogram (safe)
  const minSales = Math.min(...eda.sales);
  const maxSales = Math.max(...eda.sales);
  const range = maxSales - minSales;
  const binSize = range === 0 ? 1 : Math.ceil(range / 8);

  const histBins = [];
  for (let b = minSales; b < maxSales; b += binSize) {
    const count = eda.sales.filter(s => s >= b && s < b + binSize).length;
    histBins.push({ range: `${b}-${b + binSize}`, count });
  }

  const maxLag = Math.min(20, Math.floor(eda.sales.length / 2));
  const acfData = computeACF(eda.sales, maxLag);
  const pacfData = computePACF(eda.sales, maxLag);

  // ── STYLES ────────────────────────────────────────

  const tooltipStyle = {
    contentStyle: {
      background: "hsl(220 22% 13%)",
      border: "1px solid hsl(220 18% 20%)",
      borderRadius: 8,
      color: "hsl(210 20% 92%)",
    },
  };

  const gridStyle = { strokeDasharray: "3 3", stroke: "hsl(220 18% 20%)" };
  const tickStyle = { fontSize: 10, fill: "hsl(215 15% 55%)" };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 4</span>
        <h2 className="section-header mt-3">Exploratory Data Analysis</h2>
        <p className="text-muted-foreground mt-1">
          Mengeksplorasi pola, tren, dan distribusi data penjualan.
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Mean", value: eda.mean.toFixed(2) },
          { label: "Std Dev", value: eda.std.toFixed(2) },
          { label: "Min", value: eda.min },
          { label: "Max", value: eda.max },
        ].map(s => (
          <div key={s.label} className="stat-card text-center">
            <div className="text-xs text-muted-foreground mb-1">{s.label}</div>
            <div className="text-2xl font-bold font-mono text-primary">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Time Series */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-2">📈 Time Series</h3>
        <p className="text-xs text-muted-foreground mb-2">
          Pola penjualan dari waktu ke waktu (trend & fluktuasi).
        </p>

        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={timeSeriesData}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="week" tick={tickStyle} interval={4} />
            <YAxis tick={tickStyle} />
            <Tooltip {...tooltipStyle} />
            <Line type="monotone" dataKey="sales" stroke="hsl(174 72% 50%)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Histogram */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">Distribusi</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={histBins}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="range" tick={tickStyle} />
            <YAxis tick={tickStyle} />
            <Tooltip {...tooltipStyle} />
            <Bar dataKey="count" fill="hsl(262 60% 58%)" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Rolling */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">
          Rolling Mean & Std
        </h3>

        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={timeSeriesData}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="week" tick={tickStyle} interval={4} />
            <YAxis tick={tickStyle} />
            <Tooltip {...tooltipStyle} />

            <Line dataKey="sales" stroke="hsl(215 15% 55%)" dot={false} />
            <Line dataKey="rollingMean" stroke="hsl(174 72% 50%)" dot={false} />
            <Line
              dataKey="rollingStd"
              stroke="hsl(35 92% 60%)"
              strokeDasharray="4 4"
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ACF */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">ACF</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={acfData}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="lag" tick={tickStyle} />
            <YAxis domain={[-0.5, 1]} tick={tickStyle} />
            <Tooltip {...tooltipStyle} />
            <ReferenceLine y={acfData[0]?.upper} stroke="red" strokeDasharray="5 5" />
            <ReferenceLine y={acfData[0]?.lower} stroke="red" strokeDasharray="5 5" />
            <Bar dataKey="acf" fill="hsl(174 72% 50%)" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* PACF */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">PACF</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={pacfData}>
            <CartesianGrid {...gridStyle} />
            <XAxis dataKey="lag" tick={tickStyle} />
            <YAxis domain={[-0.5, 1]} tick={tickStyle} />
            <Tooltip {...tooltipStyle} />
            <ReferenceLine y={pacfData[0]?.upper} stroke="red" strokeDasharray="5 5" />
            <ReferenceLine y={pacfData[0]?.lower} stroke="red" strokeDasharray="5 5" />
            <Bar dataKey="pacf" fill="hsl(262 60% 58%)" />
          </BarChart>
        </ResponsiveContainer>

        <p className="text-xs text-muted-foreground mt-2 italic">
          PACF dihitung secara aproksimasi untuk visualisasi.
        </p>
      </div>

      {/* Seasonality Heatmap */}
      {eda.seasonality && eda.seasonality.length > 0 && (
        <SeasonalityHeatmap data={eda.seasonality} />
      )}
    </div>
  );
};

export default EDA;