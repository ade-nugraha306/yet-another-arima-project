import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, ReferenceLine, Area, AreaChart, ComposedChart,
} from "recharts";
import { generateWeeklyData, getRollingStats, generateACFData, getSeasonalityData } from "@/lib/mockData";

interface Props {
  productIndex: number;
}

const EDA = ({ productIndex }: Props) => {
  const data = generateWeeklyData(productIndex);
  const rollingData = getRollingStats(data);
  const acfData = generateACFData();
  const seasonData = getSeasonalityData();

  // Histogram bins
  const min = Math.min(...data.map(d => d.sales));
  const max = Math.max(...data.map(d => d.sales));
  const binSize = Math.ceil((max - min) / 8);
  const histBins = [];
  for (let b = min; b < max; b += binSize) {
    const count = data.filter(d => d.sales >= b && d.sales < b + binSize).length;
    histBins.push({ range: `${b}-${b + binSize}`, count });
  }

  // Seasonality heatmap as grid
  const months = [...new Set(seasonData.map(d => d.month))];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 4</span>
        <h2 className="section-header mt-3">Exploratory Data Analysis</h2>
        <p className="text-muted-foreground mt-1">
          Mengeksplorasi pola, tren, dan karakteristik data sebelum pemodelan.
        </p>
      </div>

      {/* Time Series Plot */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">📈 Time Series Plot</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 18% 20%)" />
            <XAxis dataKey="week" tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} interval={4} />
            <YAxis tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
            <Tooltip contentStyle={{ background: "hsl(220 22% 13%)", border: "1px solid hsl(220 18% 20%)", borderRadius: 8, color: "hsl(210 20% 92%)" }} />
            <Line type="monotone" dataKey="sales" stroke="hsl(174 72% 50%)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Histogram */}
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-3">📊 Distribusi Penjualan</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={histBins}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 18% 20%)" />
              <XAxis dataKey="range" tick={{ fontSize: 9, fill: "hsl(215 15% 55%)" }} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
              <Tooltip contentStyle={{ background: "hsl(220 22% 13%)", border: "1px solid hsl(220 18% 20%)", borderRadius: 8, color: "hsl(210 20% 92%)" }} />
              <Bar dataKey="count" fill="hsl(262 60% 58%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Rolling Mean & Std */}
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-3">📉 Rolling Mean & Std (window=4)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={rollingData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 18% 20%)" />
              <XAxis dataKey="week" tick={{ fontSize: 9, fill: "hsl(215 15% 55%)" }} interval={4} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
              <Tooltip contentStyle={{ background: "hsl(220 22% 13%)", border: "1px solid hsl(220 18% 20%)", borderRadius: 8, color: "hsl(210 20% 92%)" }} />
              <Line type="monotone" dataKey="sales" stroke="hsl(215 15% 55%)" strokeWidth={1} dot={false} name="Original" />
              <Line type="monotone" dataKey="rollingMean" stroke="hsl(174 72% 50%)" strokeWidth={2} dot={false} name="Rolling Mean" />
              <Line type="monotone" dataKey="rollingStd" stroke="hsl(35 92% 60%)" strokeWidth={2} dot={false} name="Rolling Std" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ACF */}
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-3">ACF (Autocorrelation)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={acfData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 18% 20%)" />
              <XAxis dataKey="lag" tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
              <YAxis domain={[-0.5, 1]} tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
              <Tooltip contentStyle={{ background: "hsl(220 22% 13%)", border: "1px solid hsl(220 18% 20%)", borderRadius: 8, color: "hsl(210 20% 92%)" }} />
              <ReferenceLine y={acfData[0]?.upper} stroke="hsl(350 70% 58%)" strokeDasharray="5 5" />
              <ReferenceLine y={acfData[0]?.lower} stroke="hsl(350 70% 58%)" strokeDasharray="5 5" />
              <Bar dataKey="acf" fill="hsl(174 72% 50%)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* PACF */}
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-3">PACF (Partial Autocorrelation)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={acfData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 18% 20%)" />
              <XAxis dataKey="lag" tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
              <YAxis domain={[-0.5, 1]} tick={{ fontSize: 10, fill: "hsl(215 15% 55%)" }} />
              <Tooltip contentStyle={{ background: "hsl(220 22% 13%)", border: "1px solid hsl(220 18% 20%)", borderRadius: 8, color: "hsl(210 20% 92%)" }} />
              <ReferenceLine y={acfData[0]?.upper} stroke="hsl(350 70% 58%)" strokeDasharray="5 5" />
              <ReferenceLine y={acfData[0]?.lower} stroke="hsl(350 70% 58%)" strokeDasharray="5 5" />
              <Bar dataKey="pacf" fill="hsl(262 60% 58%)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Seasonality Heatmap */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">🌡️ Seasonality Heatmap</h3>
        <div className="overflow-x-auto">
          <div className="inline-grid gap-1" style={{ gridTemplateColumns: `80px repeat(4, 1fr)` }}>
            <div className="text-xs text-muted-foreground p-1"></div>
            {["W1", "W2", "W3", "W4"].map(w => (
              <div key={w} className="text-xs text-muted-foreground p-1 text-center font-mono">{w}</div>
            ))}
            {months.map(month => (
              <>
                <div key={month} className="text-xs text-muted-foreground p-1 font-mono">{month}</div>
                {seasonData.filter(d => d.month === month).map((cell, idx) => {
                  const intensity = Math.min((cell.value - 70) / 70, 1);
                  return (
                    <div
                      key={`${month}-${idx}`}
                      className="rounded text-xs text-center p-2 font-mono font-semibold"
                      style={{
                        background: `hsl(174 72% ${20 + intensity * 35}%)`,
                        color: intensity > 0.5 ? "hsl(220 25% 10%)" : "hsl(210 20% 85%)",
                      }}
                    >
                      {cell.value}
                    </div>
                  );
                })}
              </>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EDA;
