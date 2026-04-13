// Mock data for the ARIMA forecasting dashboard

export const products = [
  "Product A - Electronics",
  "Product B - Clothing",
  "Product C - Food & Beverage",
  "Product D - Home & Garden",
];

// Generate weekly sales data (W1-W40)
export function generateWeeklyData(productIndex: number) {
  const seed = (productIndex + 1) * 17;
  const base = 100 + productIndex * 30;
  const data = [];
  for (let i = 1; i <= 40; i++) {
    const trend = i * 1.5;
    const seasonal = Math.sin((i / 4) * Math.PI) * 15;
    const noise = Math.sin(seed * i * 0.3) * 10 + Math.cos(seed * i * 0.7) * 5;
    data.push({
      week: `W${i}`,
      weekNum: i,
      sales: Math.round(base + trend + seasonal + noise),
    });
  }
  return data;
}

export function generateForecast(data: { week: string; weekNum: number; sales: number }[], horizon: number) {
  const lastVal = data[data.length - 1].sales;
  const trend = (data[data.length - 1].sales - data[0].sales) / data.length;
  const forecast = [];
  for (let i = 1; i <= horizon; i++) {
    const val = Math.round(lastVal + trend * i + Math.sin(i) * 8);
    const ci = 10 + i * 5;
    forecast.push({
      week: `W${40 + i}`,
      weekNum: 40 + i,
      forecast: val,
      upper: val + ci,
      lower: val - ci,
    });
  }
  return forecast;
}

export function generateACFData() {
  const data = [];
  for (let i = 0; i <= 20; i++) {
    data.push({
      lag: i,
      acf: i === 0 ? 1 : Math.exp(-i * 0.15) * Math.cos(i * 0.5) + (Math.random() - 0.5) * 0.05,
      pacf: i === 0 ? 1 : (i <= 3 ? 0.6 / i : (Math.random() - 0.5) * 0.12),
      upper: 1.96 / Math.sqrt(40),
      lower: -1.96 / Math.sqrt(40),
    });
  }
  return data;
}

export function getCleaningStats() {
  return {
    missingBefore: 3,
    missingAfter: 0,
    outliersBefore: 5,
    outliersAfter: 1,
    adfStatistic: -3.82,
    adfPValue: 0.0028,
    dValue: 1,
    method: "Interpolasi Linear + IQR Clipping (1.5×IQR)",
  };
}

export function getModelMetrics() {
  return {
    mse: 142.35,
    rmse: 11.93,
    mae: 9.47,
    mape: 6.82,
  };
}

export function getSeasonalityData() {
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"];
  const data = [];
  for (const month of months) {
    for (let w = 1; w <= 4; w++) {
      data.push({
        month,
        week: `W${w}`,
        value: Math.round(80 + Math.random() * 60),
      });
    }
  }
  return data;
}

export function getRollingStats(data: { week: string; weekNum: number; sales: number }[]) {
  const window = 4;
  return data.map((d, i) => {
    if (i < window - 1) return { ...d, rollingMean: null, rollingStd: null };
    const slice = data.slice(i - window + 1, i + 1).map(s => s.sales);
    const mean = slice.reduce((a, b) => a + b, 0) / window;
    const std = Math.sqrt(slice.reduce((a, b) => a + (b - mean) ** 2, 0) / window);
    return { ...d, rollingMean: Math.round(mean * 10) / 10, rollingStd: Math.round(std * 10) / 10 };
  });
}
