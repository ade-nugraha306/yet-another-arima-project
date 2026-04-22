import { useEffect, useState } from "react";
import { CheckCircle, TrendingUp, TrendingDown, Minus, Loader2 } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { evaluateProduct, type EvaluationResponse } from "@/services/api";

interface Props {
  product: string;
  horizon: number;
}

const Evaluation = ({ product }: Props) => {
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const data = await evaluateProduct(product);
        if (!cancelled) setEvaluation(data);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Gagal memuat evaluasi model");
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
        <Loader2 className="w-4 h-4 animate-spin" /> Mengevaluasi model…
      </div>
    );
  }

  if (error || !evaluation) {
    return <p className="text-sm text-destructive py-4">{error ?? "Data evaluasi tidak tersedia"}</p>;
  }

  // ── BUILD DATA ─────────────────────────────────────
  // fitted dari backend = forecast di test period (panjang = test set)
  // bukan in-sample fitted values untuk train

  const trainLen = evaluation.actual_train.length;

  const trainData = evaluation.actual_train.map((sales, i) => ({
    week: evaluation.dates_train[i],
    sales,
    predicted: null as number | null,
    type: "train",
  }));

  const testData = evaluation.actual_test.map((sales, i) => ({
    week: evaluation.dates_test[i],
    sales,
    predicted: evaluation.fitted?.[i] ?? null,  // index i, bukan trainLen + i
    type: "test",
  }));

  const splitData = [...trainData, ...testData];
  const splitWeek = evaluation.dates_train[trainLen - 1];

  // ── TREND CALCULATION (SAFE) ───────────────────────

  const allActual = [...evaluation.actual_train, ...evaluation.actual_test];

  const avgGrowth =
    allActual.length > 1 && allActual[0] !== 0
      ? ((allActual[allActual.length - 1] - allActual[0]) / allActual[0]) * 100
      : 0;

  const trendClass =
    avgGrowth > 15 ? "FAST" :
    avgGrowth > 3 ? "MEDIUM" :
    "SLOW";

  const trendColor =
    trendClass === "FAST"
      ? "text-success"
      : trendClass === "MEDIUM"
      ? "text-warning"
      : "text-destructive";

  const TrendIcon =
    trendClass === "FAST"
      ? TrendingUp
      : trendClass === "SLOW"
      ? TrendingDown
      : Minus;

  // ── METRICS ───────────────────────────────────────

  const metricCards = [
    { label: "MAE", value: evaluation.mae.toFixed(2), desc: "Mean Absolute Error" },
    { label: "RMSE", value: evaluation.rmse.toFixed(2), desc: "Root Mean Squared Error" },
    { label: "MAPE", value: `${evaluation.mape.toFixed(2)}%`, desc: "Mean Abs. Percentage Error" },
  ];

  // ── STYLES ────────────────────────────────────────

  const tooltipStyle = {
    contentStyle: {
      background: "hsl(220 22% 13%)",
      border: "1px solid hsl(220 18% 20%)",
      borderRadius: 8,
      color: "hsl(210 20% 92%)",
    },
  };

  const tickStyle = {
    fontSize: 10,
    fill: "hsl(215 15% 55%)",
  };

  // ── UI ────────────────────────────────────────────

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 6</span>
        <h2 className="section-header mt-3">Evaluation & Validation</h2>
        <p className="text-muted-foreground mt-1">
          Mengevaluasi performa model berdasarkan data train dan test.
        </p>
      </div>

      {/* MODEL INFO */}
      <div className="stat-card glow-border">
        <p className="text-sm text-muted-foreground">
          Model:
          <span className="ml-2 font-mono font-bold text-primary">
            ARIMA({evaluation.order[0]}, {evaluation.order[1]}, {evaluation.order[2]})
          </span>
        </p>
      </div>

      {/* CHART */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-2">
          📊 Train-Test Split & Prediction
        </h3>
        <div className="flex gap-4 mb-3">
          <span className="text-xs px-2 py-1 rounded bg-primary/15 text-primary">■ Train ({trainLen} minggu)</span>
          <span className="text-xs px-2 py-1 rounded bg-warning/15 text-warning">■ Test ({evaluation.actual_test.length} minggu)</span>
          <span className="text-xs px-2 py-1 rounded bg-purple-500/15 text-purple-400">■ Predicted</span>
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={splitData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 18% 20%)" />

            <XAxis dataKey="week" tick={tickStyle} interval={4} />
            <YAxis tick={tickStyle} />

            <Tooltip
              {...tooltipStyle}
              formatter={(value: number, name: string) => [
                value?.toFixed?.(2) ?? value,
                name,
              ]}
            />

            <ReferenceLine
              x={splitWeek}
              stroke="hsl(35 92% 60%)"
              strokeDasharray="5 5"
              label={{ value: "Split", fill: "hsl(35 92% 60%)", fontSize: 10 }}
            />

            <Line
              dataKey="sales"
              stroke="hsl(174 72% 50%)"
              strokeWidth={2}
              dot={false}
              name="Actual"
            />

            <Line
              dataKey="predicted"
              stroke="hsl(262 60% 58%)"
              strokeWidth={2}
              strokeDasharray="4 2"
              dot={false}
              name="Test Prediction"
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* METRICS */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {metricCards.map((m) => (
          <div key={m.label} className="stat-card text-center">
            <div className="text-xs text-muted-foreground mb-1">{m.desc}</div>
            <div className="text-2xl font-bold font-mono text-primary">{m.value}</div>
            <div className="text-sm text-muted-foreground">{m.label}</div>
          </div>
        ))}
      </div>

      {/* TREND */}
      <div className="stat-card glow-border">
        <h3 className="text-sm font-semibold text-primary mb-4 flex items-center gap-2">
          <CheckCircle className="w-4 h-4" /> Klasifikasi Tren
        </h3>

        <div className="flex items-center justify-center gap-6">
          <TrendIcon className={`w-12 h-12 ${trendColor}`} />

          <div>
            <div className={`text-4xl font-extrabold ${trendColor}`}>
              {trendClass}
            </div>

            <div className="text-sm text-muted-foreground">
              Growth:
              <span className="ml-2 font-mono font-semibold">
                {avgGrowth.toFixed(1)}%
              </span>{" "}
              selama {evaluation.actual_train.length + evaluation.actual_test.length} minggu
            </div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          {([
            { label: "SLOW",   range: "< 3%",      color: "bg-destructive/15 text-destructive" },
            { label: "MEDIUM", range: "3% – 15%",  color: "bg-warning/15 text-warning" },
            { label: "FAST",   range: "> 15%",      color: "bg-success/15 text-success" },
          ] as const).map(t => (
            <div
              key={t.label}
              className={`p-2 rounded ${t.color} ${trendClass === t.label ? "ring-1 ring-current" : "opacity-50"}`}
            >
              <div className="font-bold">{t.label}</div>
              <div>{t.range}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Evaluation;