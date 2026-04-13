import { Target, TrendingUp, Calendar, Package } from "lucide-react";

const BusinessUnderstanding = () => {
  const objectives = [
    {
      icon: Target,
      title: "Tujuan Proyek",
      desc: "Melakukan forecast penjualan mingguan untuk perencanaan inventory yang lebih akurat dan efisien.",
    },
    {
      icon: Calendar,
      title: "Scope Dataset",
      desc: "Data penjualan mingguan dari W1 hingga W40 (40 minggu observasi) untuk setiap produk.",
    },
    {
      icon: TrendingUp,
      title: "Horizon Prediksi",
      desc: "Memprediksi 5 minggu ke depan (W41–W45) menggunakan model ARIMA.",
    },
    {
      icon: Package,
      title: "Tujuan Bisnis",
      desc: "Inventory planning dan klasifikasi tren produk (FAST / MEDIUM / SLOW) untuk pengambilan keputusan.",
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 1</span>
        <h2 className="section-header mt-3">Business Understanding</h2>
        <p className="text-muted-foreground mt-1">
          Mendefinisikan tujuan bisnis, scope analisis, dan metrik keberhasilan proyek forecasting.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {objectives.map((obj) => (
          <div key={obj.title} className="stat-card flex gap-4 items-start">
            <div className="p-2.5 rounded-lg bg-primary/10 text-primary shrink-0">
              <obj.icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">{obj.title}</h3>
              <p className="text-sm text-muted-foreground mt-1">{obj.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="stat-card glow-border">
        <h3 className="text-sm font-semibold text-primary mb-2">📋 Ringkasan Proyek</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          {[
            { label: "Metode", value: "ARIMA" },
            { label: "Frekuensi", value: "Mingguan" },
            { label: "Horizon", value: "5 Minggu" },
            { label: "Klasifikasi", value: "3 Kategori" },
          ].map((item) => (
            <div key={item.label}>
              <div className="text-lg font-bold text-foreground">{item.value}</div>
              <div className="text-xs text-muted-foreground">{item.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default BusinessUnderstanding;
