import { useEffect, useState } from "react";
import { Loader2, TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Legend,
} from "recharts";
import { getEvaluation, type EvaluationResponse } from "@/services/api";

interface Props {
  family: string;
}

// Klasifikasi tren: Fast (naik >10%), Slow (turun >10%), Medium (perubahan <=10%)
function classifyTrend(train: number[], test: number[]): {
  label: "Fast" | "Medium" | "Slow";
  color: string;
  icon: JSX.Element;
  description: string;
} {
  const trainMean = train.reduce((a, b) => a + b, 0) / train.length;
  const testMean = test.reduce((a, b) => a + b, 0) / test.length;
  const percentChange = ((testMean - trainMean) / trainMean) * 100;
  const absPercentChange = Math.abs(percentChange);

  let label: "Fast" | "Medium" | "Slow";
  let color: string;

  if (percentChange > 10) {
    label = "Fast";
    color = "text-orange-500";
  } else if (percentChange < -10) {
    label = "Slow";
    color = "text-blue-400";
  } else {
    label = "Medium";
    color = "text-yellow-500";
  }

  // Ikon dan deskripsi
  let icon: JSX.Element;
  let directionText = "";
  if (percentChange > 0) {
    icon = <TrendingUp className="w-5 h-5" />;
    directionText = `meningkat ${absPercentChange.toFixed(1)}%`;
  } else if (percentChange < 0) {
    icon = <TrendingDown className="w-5 h-5" />;
    directionText = `menurun ${absPercentChange.toFixed(1)}%`;
  } else {
    icon = <Minus className="w-5 h-5" />;
    directionText = "stabil (0%)";
  }

  const description = `Perubahan ${directionText} (kategori ${label})`;
  return { label, color, icon, description };
}

const Evaluation = ({ family }: Props) => {
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getEvaluation(family);
        if (!cancelled) setEvaluation(data);
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Gagal memuat evaluasi model");
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
        <Loader2 className="w-4 h-4 animate-spin" /> Mengevaluasi model…
      </div>
    );
  }

  if (error || !evaluation) {
    return <p className="text-sm text-destructive py-4">{error ?? "Data evaluasi tidak tersedia"}</p>;
  }

  const trainLen = evaluation.actual_train.length;
  const trainData = evaluation.actual_train.map((sales, i) => ({
    week: evaluation.dates_train[i],
    sales,
    predicted: null as number | null,
  }));
  const testData = evaluation.actual_test.map((sales, i) => ({
    week: evaluation.dates_test[i],
    sales,
    predicted: evaluation.fitted?.[i] ?? null,
  }));
  const splitData = [...trainData, ...testData];
  const splitWeek = evaluation.dates_train[trainLen - 1];
  const trend = classifyTrend(evaluation.actual_train, evaluation.actual_test);

  const tooltipStyle = {
    contentStyle: {
      background: "hsl(220 22% 13%)",
      border: "1px solid hsl(220 18% 20%)",
      borderRadius: 8,
      color: "hsl(210 20% 92%)",
    },
  };
  const tickStyle = { fontSize: 10, fill: "hsl(215 15% 55%)" };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 6</span>
        <h2 className="section-header mt-3">Evaluation &amp; Validation</h2>
        <p className="text-muted-foreground mt-1">
          Mengevaluasi performa model ARIMA untuk family{" "}
          <span className="text-primary font-semibold">{family}</span>.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="stat-card glow-border flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">Model</p>
            <p className="font-mono font-bold text-primary text-lg">
              ARIMA({evaluation.order[0]}, {evaluation.order[1]}, {evaluation.order[2]})
            </p>
          </div>
          {evaluation.aic !== null && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">AIC</p>
              <p className="font-mono font-bold text-foreground">{evaluation.aic}</p>
            </div>
          )}
        </div>

        {/* Klasifikasi Tren: Fast / Medium / Slow */}
        <div className="stat-card flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">Klasifikasi Tren</p>
            <div className={`flex items-center gap-2 font-bold text-lg ${trend.color}`}>
              {trend.icon}
              <span>{trend.label}</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">{trend.description}</p>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <div>Train avg: {(evaluation.actual_train.reduce((a,b)=>a+b,0)/evaluation.actual_train.length).toFixed(2)}</div>
            <div>Test avg: {(evaluation.actual_test.reduce((a,b)=>a+b,0)/evaluation.actual_test.length).toFixed(2)}</div>
          </div>
        </div>
      </div>

      {/* Train/Test Chart */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-2">📊 Train-Test Split &amp; Prediction</h3>
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
            <Tooltip {...tooltipStyle} formatter={(value: number) => value?.toFixed?.(2) ?? value} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <ReferenceLine x={splitWeek} stroke="hsl(35 92% 60%)" strokeDasharray="5 5" label={{ value: "Split", fill: "hsl(35 92% 60%)", fontSize: 10 }} />
            <Line dataKey="sales" stroke="hsl(174 72% 50%)" strokeWidth={2} dot={false} name="Actual" />
            <Line dataKey="predicted" stroke="hsl(262 60% 58%)" strokeWidth={2} strokeDasharray="4 2" dot={false} name="Test Prediction" connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "MAE", value: evaluation.mae.toFixed(4), desc: "Mean Absolute Error" },
          { label: "RMSE", value: evaluation.rmse.toFixed(4), desc: "Root Mean Squared Error" },
          { label: "sMAPE", value: `${evaluation.smape.toFixed(2)}%`, desc: "Symmetric Mean Abs. Percentage Error" },
        ].map(m => (
          <div key={m.label} className="stat-card text-center">
            <div className="text-xs text-muted-foreground mb-1">{m.desc}</div>
            <div className="text-2xl font-bold font-mono text-primary">{m.value}</div>
            <div className="text-sm text-muted-foreground">{m.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Evaluation;