// src/components/stages/Modeling.tsx
import { useEffect, useState, useCallback } from "react";
import { Settings2, Zap, BarChart3, RefreshCw, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
  Legend,
  ReferenceLine,
} from "recharts";
import { forecastProduct, ForecastResponse } from "@/services/api";
import { generateWeeklyData } from "@/lib/mockData";

interface Props {
  productIndex: number;
  selectedProduct: string;
  horizon: number;
}

const Modeling = ({ productIndex, selectedProduct, horizon }: Props) => {
  const [autoArima, setAutoArima] = useState(true);
  const [p, setP] = useState(1);
  const [d, setD] = useState(1);
  const [q, setQ] = useState(1);

  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data historis (mock) — diganti dengan endpoint /history jika tersedia
  const historicalData = generateWeeklyData(productIndex);

  // ── Gabung historis + forecast untuk chart ──────────────────
  const combinedData = [
    ...historicalData.map((row) => ({
      week: row.week,
      sales: row.sales,
      forecast: null as number | null,
      upper: null as number | null,
      lower: null as number | null,
    })),
    ...(forecastData
      ? forecastData.forecast.map((val, i) => ({
          week: forecastData.weeks[i],
          sales: null as number | null,
          forecast: val,
          upper: forecastData.upper[i],
          lower: forecastData.lower[i],
        }))
      : []),
  ];

  // Label titik pemisah antara historis & forecast di chart
  const splitWeek = historicalData.at(-1)?.week;

  // ── Fetch forecast dari backend ──────────────────────────────
  const handleForecast = useCallback(async () => {
    if (!selectedProduct) return;
    setLoading(true);
    setError(null);
    try {
      const res = await forecastProduct(selectedProduct, horizon);
      setForecastData(res);
      // Sync tampilan manual p/d/q dengan hasil auto-ARIMA
      if (res.order) {
        setP(res.order[0]);
        setD(res.order[1]);
        setQ(res.order[2]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal mengambil forecast.";
      setError(msg);
      setForecastData(null);
    } finally {
      setLoading(false);
    }
  }, [selectedProduct, horizon]);

  useEffect(() => {
    handleForecast();
  }, [handleForecast]);

  // ── Display values ────────────────────────────────────────────
  const displayOrder = forecastData?.order ?? (autoArima ? null : [p, d, q]);
  const displayAIC   = forecastData?.aic != null ? forecastData.aic.toFixed(2) : "—";
  const displayLabel = (v: number | null | undefined) =>
    loading ? "…" : (v ?? "—").toString();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <span className="section-badge">Tahap 5</span>
        <h2 className="section-header mt-3">Modeling & Machine Learning</h2>
        <p className="text-muted-foreground mt-1">
          Model ARIMA untuk forecasting penjualan mingguan —{" "}
          <span className="text-primary font-medium">{selectedProduct || "—"}</span>
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Gagal menghubungi backend</p>
            <p className="text-xs mt-0.5 opacity-80">{error}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* ── Config Panel ── */}
        <div className="stat-card space-y-4">
          <h3 className="text-sm font-semibold text-primary flex items-center gap-2">
            <Settings2 className="w-4 h-4" /> Konfigurasi Model
          </h3>

          <div className="flex items-center justify-between">
            <Label className="text-sm">Auto ARIMA</Label>
            <Switch checked={autoArima} onCheckedChange={setAutoArima} />
          </div>

          {!autoArima && (
            <div className="space-y-3">
              {[
                { label: "p (AR order)", val: p, set: setP, max: 5 },
                { label: "d (Differencing)", val: d, set: setD, max: 2 },
                { label: "q (MA order)", val: q, set: setQ, max: 5 },
              ].map(({ label, val, set, max }) => (
                <div key={label}>
                  <Label className="text-xs text-muted-foreground">{label}</Label>
                  <Input
                    type="number"
                    min={0}
                    max={max}
                    value={val}
                    onChange={(e) => set(Number(e.target.value))}
                    className="bg-secondary border-border"
                  />
                </div>
              ))}
            </div>
          )}

          {autoArima && (
            <div className="p-2 rounded bg-primary/10 text-xs text-primary">
              <Zap className="w-3 h-3 inline mr-1" />
              Auto ARIMA memilih parameter optimal berdasarkan AIC minimum.
            </div>
          )}

          <Button
            onClick={handleForecast}
            disabled={loading || !selectedProduct}
            size="sm"
            className="w-full"
          >
            {loading
              ? <><RefreshCw className="w-3 h-3 mr-2 animate-spin" />Memproses…</>
              : <><Zap className="w-3 h-3 mr-2" />Jalankan Forecast</>
            }
          </Button>
        </div>

        {/* ── Parameter Panel ── */}
        <div className="stat-card md:col-span-2">
          <h3 className="text-sm font-semibold text-primary flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4" /> Parameter Model Terpilih
          </h3>

          <div className="grid grid-cols-4 gap-3 text-center mb-4">
            {[
              { label: "p (AR)", val: displayOrder?.[0] },
              { label: "d (I)",  val: displayOrder?.[1] },
              { label: "q (MA)", val: displayOrder?.[2] },
              { label: "AIC",    val: displayAIC, warn: true },
            ].map(({ label, val, warn }) => (
              <div key={label} className="p-3 rounded-lg bg-secondary">
                <div className={`text-2xl font-bold font-mono ${warn ? "text-warning" : "text-primary"}`}>
                  {loading ? <span className="animate-pulse text-lg">…</span> : (val ?? "—")}
                </div>
                <div className="text-xs text-muted-foreground">{label}</div>
              </div>
            ))}
          </div>

          <div className="font-mono text-sm bg-secondary/50 p-3 rounded text-muted-foreground">
            {displayOrder
              ? `ARIMA(${displayOrder[0]},${displayOrder[1]},${displayOrder[2]})`
              : "ARIMA(?,?,?)"
            }{" "}
            — Forecast Horizon: {horizon} minggu
          </div>

          {/* Last known Sales value */}
          {forecastData?.last_sales != null && (
            <p className="text-xs text-muted-foreground mt-2">
              Penjualan terakhir:{" "}
              <span className="text-foreground font-medium">
                {forecastData.last_sales.toLocaleString("id-ID")}
              </span>{" "}
              unit
            </p>
          )}
        </div>
      </div>

      {/* ── Forecast Chart ── */}
      <div className="stat-card glow-border">
        <h3 className="text-sm font-semibold text-primary mb-3">
          📈 Forecast dengan Confidence Interval (95%)
        </h3>

        {loading ? (
          <div className="flex flex-col items-center justify-center h-[300px] gap-2 text-muted-foreground text-sm">
            <RefreshCw className="w-5 h-5 animate-spin text-primary" />
            <span>Menjalankan Auto ARIMA…</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={combinedData}>
              <defs>
                <linearGradient id="ciGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="hsl(174 72% 50%)" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="hsl(174 72% 50%)" stopOpacity={0} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 18% 20%)" />
              <XAxis
                dataKey="week"
                tick={{ fontSize: 9, fill: "hsl(215 15% 55%)" }}
                interval={4}
              />
              <YAxis tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
              <Tooltip
                contentStyle={{
                  background: "hsl(220 22% 13%)",
                  border: "1px solid hsl(220 18% 20%)",
                  borderRadius: 8,
                  color: "hsl(210 20% 92%)",
                }}
                formatter={(v: number) => v != null ? v.toLocaleString("id-ID") : "—"}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: "hsl(215 15% 55%)" }} />

              {/* Garis pemisah historis / forecast */}
              {splitWeek && (
                <ReferenceLine
                  x={splitWeek}
                  stroke="hsl(215 15% 40%)"
                  strokeDasharray="4 4"
                  label={{ value: "▶ Forecast", position: "insideTopRight", fontSize: 10, fill: "hsl(35 92% 60%)" }}
                />
              )}

              {/* CI band */}
              <Area
                type="monotone"
                dataKey="upper"
                stroke="none"
                fill="url(#ciGrad)"
                legendType="none"
              />
              <Area
                type="monotone"
                dataKey="lower"
                stroke="none"
                fill="hsl(220 22% 13%)"
                legendType="none"
              />

              {/* CI lines */}
              <Line type="monotone" dataKey="upper" stroke="hsl(174 72% 50% / 0.35)" strokeWidth={1} strokeDasharray="3 3" dot={false} name="Upper CI" />
              <Line type="monotone" dataKey="lower" stroke="hsl(174 72% 50% / 0.35)" strokeWidth={1} strokeDasharray="3 3" dot={false} name="Lower CI" />

              {/* Aktual */}
              <Line type="monotone" dataKey="sales"    stroke="hsl(174 72% 50%)" strokeWidth={2} dot={false} name="Aktual" />

              {/* Forecast */}
              <Line
                type="monotone"
                dataKey="forecast"
                stroke="hsl(35 92% 60%)"
                strokeWidth={2}
                strokeDasharray="6 3"
                dot={{ r: 4, fill: "hsl(35 92% 60%)", strokeWidth: 0 }}
                activeDot={{ r: 6 }}
                name="Forecast"
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default Modeling;