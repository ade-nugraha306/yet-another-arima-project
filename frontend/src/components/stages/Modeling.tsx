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
import { forecastProduct, getEDA, ForecastResponse } from "@/services/api";

interface Props {
  selectedProduct: string;
  horizon: number;
}

const Modeling = ({ selectedProduct, horizon }: Props) => {
  const [autoArima, setAutoArima] = useState(true);
  const [p, setP] = useState(1);
  const [d, setD] = useState(1);
  const [q, setQ] = useState(1);

  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [historicalData, setHistoricalData] = useState<{ week: string; sales: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── HISTORICAL ───────────────────────────────
  useEffect(() => {
    if (!selectedProduct) return;

    let cancelled = false;

    getEDA(selectedProduct)
      .then((eda) => {
        if (cancelled) return;

        setHistoricalData(
          eda.dates.map((d, i) => ({
            week: d,
            sales: eda.sales[i],
          }))
        );
      })
      .catch((err) => {
        console.warn("EDA fetch gagal:", err);
      });

    return () => { cancelled = true };
  }, [selectedProduct]);

  // ── FORECAST ────────────────────────────────
  const handleForecast = useCallback(async () => {
    if (!selectedProduct) return;

    setLoading(true);
    setError(null);

    try {
      // ⚠️ NOTE:
      // backend saat ini belum support manual p,d,q
      const res = await forecastProduct(selectedProduct, horizon);

      setForecastData(res);

      if (res.order) {
        setP(res.order[0]);
        setD(res.order[1]);
        setQ(res.order[2]);
      }

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gagal forecast.";
      setError(msg);
      setForecastData(null);
    } finally {
      setLoading(false);
    }
  }, [selectedProduct, horizon]);

  useEffect(() => {
    handleForecast();
  }, [handleForecast]);

  // ── COMBINED DATA ───────────────────────────
  const combinedData = [
    ...historicalData.map((row) => ({
      week: row.week,
      sales: row.sales,
      forecast: null,
      upper: null,
      lower: null,
    })),
    ...(forecastData
      ? forecastData.forecast.map((val, i) => ({
          week: forecastData.weeks[i],
          sales: null,
          forecast: val,
          upper: forecastData.upper[i],
          lower: forecastData.lower[i],
        }))
      : []),
  ];

  const splitWeek = historicalData.at(-1)?.week;

  const displayOrder = forecastData?.order ?? (autoArima ? null : [p, d, q]);

  // ── UI ──────────────────────────────────────
  return (
    <div className="space-y-6 animate-fade-in">

      {/* HEADER */}
      <div>
        <span className="section-badge">Tahap 5</span>
        <h2 className="section-header mt-3">Modeling & Machine Learning</h2>
        <p className="text-muted-foreground mt-1">
          ARIMA forecasting —{" "}
          <span className="text-primary font-medium">{selectedProduct || "—"}</span>
        </p>
      </div>

      {/* ERROR */}
      {error && (
        <div className="flex gap-2 p-3 rounded bg-destructive/10 text-destructive text-sm">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* CONFIG */}
      <div className="stat-card space-y-3">
        <div className="flex justify-between items-center">
          <Label>Auto ARIMA</Label>
          <Switch checked={autoArima} onCheckedChange={setAutoArima} />
        </div>

        {!autoArima && (
          <div className="grid grid-cols-3 gap-2">
            {[p, d, q].map((val, i) => (
              <Input
                key={i}
                type="number"
                value={val}
                onChange={(e) =>
                  [setP, setD, setQ][i](Number(e.target.value))
                }
              />
            ))}
          </div>
        )}

        <Button onClick={handleForecast} disabled={loading}>
          {loading ? "Processing..." : "Run Forecast"}
        </Button>
      </div>

      {/* PARAM */}
      <div className="stat-card">
        <p className="font-mono">
          {displayOrder
            ? `ARIMA(${displayOrder[0]},${displayOrder[1]},${displayOrder[2]})`
            : "ARIMA(auto)"}
        </p>
      </div>

      {/* CHART */}
      <div className="stat-card">
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={combinedData}>
            <CartesianGrid strokeDasharray="3 3" />

            <XAxis dataKey="week" />
            <YAxis />

            <Tooltip />

            {splitWeek && <ReferenceLine x={splitWeek} stroke="gray" />}

            <Area dataKey="upper" fillOpacity={0.1} stroke="none" />
            <Area dataKey="lower" fillOpacity={0.1} stroke="none" />

            <Line dataKey="sales" stroke="green" />
            <Line dataKey="forecast" stroke="orange" strokeDasharray="5 3" />
          </ComposedChart>
        </ResponsiveContainer>

        {/* ⚠️ WARNING */}
        <p className="text-xs text-muted-foreground mt-2">
          Catatan: hasil forecast mengikuti transformasi model (scaling/differencing).
        </p>
      </div>
    </div>
  );
};

export default Modeling;