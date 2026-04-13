import { CheckCircle, TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { generateWeeklyData, generateForecast, getModelMetrics } from "@/lib/mockData";

interface Props {
  productIndex: number;
  horizon: number;
}

const Evaluation = ({ productIndex, horizon }: Props) => {
  const data = generateWeeklyData(productIndex);
  const metrics = getModelMetrics();
  const forecast = generateForecast(data, horizon);

  const trainSize = Math.floor(data.length * 0.8);
  const trainData = data.slice(0, trainSize);
  const testData = data.slice(trainSize);

  // Simulated test forecast
  const testForecast = testData.map((d, i) => ({
    ...d,
    predicted: d.sales + Math.round((Math.sin(i) * 8)),
  }));

  const splitData = [
    ...trainData.map(d => ({ ...d, type: "train", predicted: null as number | null })),
    ...testForecast.map(d => ({ ...d, type: "test" })),
  ];

  // Trend classification
  const avgGrowth = ((data[data.length - 1].sales - data[0].sales) / data[0].sales) * 100;
  const trendClass = avgGrowth > 20 ? "FAST" : avgGrowth > 5 ? "MEDIUM" : "SLOW";
  const trendColor = trendClass === "FAST" ? "text-success" : trendClass === "MEDIUM" ? "text-warning" : "text-destructive";
  const TrendIcon = trendClass === "FAST" ? TrendingUp : trendClass === "SLOW" ? TrendingDown : Minus;

  const metricCards = [
    { label: "MSE", value: metrics.mse, desc: "Mean Squared Error" },
    { label: "RMSE", value: metrics.rmse, desc: "Root Mean Squared Error" },
    { label: "MAE", value: metrics.mae, desc: "Mean Absolute Error" },
    { label: "MAPE", value: `${metrics.mape}%`, desc: "Mean Abs. Percentage Error" },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 6</span>
        <h2 className="section-header mt-3">Evaluation & Validation</h2>
        <p className="text-muted-foreground mt-1">
          Mengevaluasi performa model dan mengklasifikasikan tren penjualan produk.
        </p>
      </div>

      {/* Train-Test Split */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">📊 Train-Test Split & Prediksi</h3>
        <div className="flex gap-4 mb-3">
          <span className="text-xs px-2 py-1 rounded bg-primary/15 text-primary">■ Train ({trainSize} minggu)</span>
          <span className="text-xs px-2 py-1 rounded bg-warning/15 text-warning">■ Test ({data.length - trainSize} minggu)</span>
          <span className="text-xs px-2 py-1 rounded bg-accent/15 text-accent-foreground">■ Predicted</span>
        </div>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={splitData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 18% 20%)" />
            <XAxis dataKey="week" tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} interval={4} />
            <YAxis tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
            <Tooltip contentStyle={{ background: "hsl(220 22% 13%)", border: "1px solid hsl(220 18% 20%)", borderRadius: 8, color: "hsl(210 20% 92%)" }} />
            <ReferenceLine x={`W${trainSize}`} stroke="hsl(35 92% 60%)" strokeDasharray="5 5" label={{ value: "Split", fill: "hsl(35 92% 60%)", fontSize: 10 }} />
            <Line type="monotone" dataKey="sales" stroke="hsl(174 72% 50%)" strokeWidth={2} dot={false} name="Actual" />
            <Line type="monotone" dataKey="predicted" stroke="hsl(262 60% 58%)" strokeWidth={2} strokeDasharray="4 2" dot={false} name="Predicted" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {metricCards.map(m => (
          <div key={m.label} className="stat-card text-center">
            <div className="text-xs text-muted-foreground mb-1">{m.desc}</div>
            <div className="text-2xl font-bold font-mono text-primary">{m.value}</div>
            <div className="text-sm font-semibold text-muted-foreground">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Trend Classification */}
      <div className="stat-card glow-border">
        <h3 className="text-sm font-semibold text-primary mb-4 flex items-center gap-2">
          <CheckCircle className="w-4 h-4" /> Klasifikasi Tren Penjualan
        </h3>
        <div className="flex items-center justify-center gap-6">
          <TrendIcon className={`w-12 h-12 ${trendColor}`} />
          <div>
            <div className={`text-4xl font-extrabold ${trendColor}`}>{trendClass}</div>
            <div className="text-sm text-muted-foreground">
              Pertumbuhan: <span className="font-mono font-semibold">{avgGrowth.toFixed(1)}%</span> selama 40 minggu
            </div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          {[
            { label: "SLOW", range: "< 5%", color: "bg-destructive/15 text-destructive" },
            { label: "MEDIUM", range: "5% – 20%", color: "bg-warning/15 text-warning" },
            { label: "FAST", range: "> 20%", color: "bg-success/15 text-success" },
          ].map(t => (
            <div key={t.label} className={`p-2 rounded ${t.color} ${trendClass === t.label ? "ring-1 ring-current" : "opacity-50"}`}>
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
