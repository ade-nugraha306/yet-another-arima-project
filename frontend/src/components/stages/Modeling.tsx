// src/components/stages/Modeling.tsx
import { useEffect, useState, useCallback } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Area, ComposedChart, Legend, ReferenceLine,
} from "recharts";
import { getModelling, type ModellingResponse } from "@/services/api";

interface Props {
  selectedFamily: string;
  horizon: number;
}

const Modeling = ({ selectedFamily, horizon }: Props) => {
  const [result, setResult] = useState<ModellingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleForecast = useCallback(async () => {
    if (!selectedFamily) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getModelling(selectedFamily, horizon);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal menjalankan forecast.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [selectedFamily, horizon]);

  // Auto-run on mount and when family/horizon changes
  useEffect(() => {
    handleForecast();
  }, [handleForecast]);

  // ── Combined chart data ───────────────────────────────────────
  const combinedData = result
    ? [
        // Historical
        ...result.historical_weeks.map((w, i) => ({
          week: w,
          sales: result.historical_sales[i],
          forecast: null as number | null,
          upper: null as number | null,
          lower: null as number | null,
        })),
        // Forecast
        ...result.forecast_dates.map((d, i) => ({
          week: d,
          sales: null as number | null,
          forecast: result.forecast[i],
          upper: result.upper[i],
          lower: result.lower[i],
        })),
      ]
    : [];

  const splitWeek = result?.historical_weeks.at(-1);

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

      {/* Header */}
      <div>
        <span className="section-badge">Tahap 5</span>
        <h2 className="section-header mt-3">Modeling &amp; Forecasting</h2>
        <p className="text-muted-foreground mt-1">
          Auto ARIMA forecasting —{" "}
          <span className="text-primary font-medium">{selectedFamily || "—"}</span>
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="flex gap-2 p-3 rounded bg-destructive/10 text-destructive text-sm">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Config */}
      <div className="stat-card flex items-center gap-4">
        <div className="flex-1">
          <p className="text-xs text-muted-foreground">Model</p>
          <p className="font-mono font-bold text-foreground">
            {result
              ? `ARIMA(${result.order[0]}, ${result.order[1]}, ${result.order[2]})`
              : "auto_arima() — menentukan order otomatis"}
          </p>
        </div>
        {result?.aic !== null && result?.aic !== undefined && (
          <div className="text-center">
            <p className="text-xs text-muted-foreground">AIC</p>
            <p className="font-mono text-lg font-bold text-primary">{result.aic}</p>
          </div>
        )}
        <Button onClick={handleForecast} disabled={loading} size="sm">
          {loading ? (
            <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Processing…</>
          ) : (
            "Re-run Forecast"
          )}
        </Button>
      </div>

      {/* Forecast metrics */}
      {result && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Order (p,d,q)", value: `(${result.order.join(",")})` },
            { label: "AIC",           value: result.aic?.toFixed(2) ?? "—" },
            { label: "Horizon",       value: `${result.horizon} minggu` },
            { label: "Last Sales",    value: result.last_sales.toLocaleString() },
          ].map(m => (
            <div key={m.label} className="stat-card text-center">
              <div className="text-xs text-muted-foreground mb-1">{m.label}</div>
              <div className="text-lg font-bold font-mono text-primary">{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Loading state */}
      {loading && !result && (
        <div className="stat-card flex items-center gap-3 text-muted-foreground text-sm py-8 justify-center">
          <Loader2 className="w-5 h-5 animate-spin" />
          Menjalankan auto_arima()…
        </div>
      )}

      {/* Chart */}
      {result && (
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-3">
            📈 Historical + Forecast{" "}
            <span className="font-normal text-muted-foreground">(with 95% CI)</span>
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={combinedData}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="week" tick={tickStyle} interval={4} />
              <YAxis tick={tickStyle} />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />

              {splitWeek && (
                <ReferenceLine
                  x={splitWeek}
                  stroke="hsl(35 92% 60%)"
                  strokeDasharray="5 5"
                  label={{ value: "Now", fill: "hsl(35 92% 60%)", fontSize: 10 }}
                />
              )}

              <Area
                dataKey="upper"
                fill="hsl(174 72% 50%)"
                stroke="none"
                fillOpacity={0.15}
                name="Upper CI"
              />
              <Area
                dataKey="lower"
                fill="hsl(220 22% 13%)"
                stroke="none"
                fillOpacity={1}
                name="Lower CI"
              />

              <Line
                type="monotone"
                dataKey="sales"
                stroke="hsl(174 72% 50%)"
                strokeWidth={2}
                dot={false}
                name="Historical"
              />
              <Line
                type="monotone"
                dataKey="forecast"
                stroke="hsl(35 92% 60%)"
                strokeWidth={2}
                strokeDasharray="5 3"
                dot={{ r: 3, fill: "hsl(35 92% 60%)" }}
                name="Forecast"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Forecast table */}
      {result && (
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-3">
            📋 Tabel Forecast {result.horizon} Minggu ke Depan
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground text-xs">
                  <th className="text-left py-2 pr-4">Tanggal</th>
                  <th className="text-right py-2 pr-4">Forecast</th>
                  <th className="text-right py-2 pr-4">Lower (95%)</th>
                  <th className="text-right py-2">Upper (95%)</th>
                </tr>
              </thead>
              <tbody>
                {result.forecast_dates.map((d, i) => (
                  <tr key={d} className="border-b border-border/50">
                    <td className="py-2 pr-4 font-mono text-xs">{d}</td>
                    <td className="py-2 pr-4 text-right font-bold text-primary font-mono">
                      {result.forecast[i].toLocaleString()}
                    </td>
                    <td className="py-2 pr-4 text-right text-muted-foreground font-mono text-xs">
                      {result.lower[i].toLocaleString()}
                    </td>
                    <td className="py-2 text-right text-muted-foreground font-mono text-xs">
                      {result.upper[i].toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Modeling;