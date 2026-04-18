import { useEffect, useState } from "react";
import { CheckCircle2, Beaker, Loader2 } from "lucide-react";
import { getEDA, type EDAResponse } from "@/services/api";

interface Props {
  product: string;
}

const DataPreparation = ({ product }: Props) => {
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
          setError(e instanceof Error ? e.message : "Gagal memuat data");
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
        <Loader2 className="w-4 h-4 animate-spin" /> Memuat hasil preparation…
      </div>
    );
  }

  if (error || !eda) {
    return <p className="text-sm text-destructive py-4">{error ?? "Data tidak tersedia"}</p>;
  }

  const dValue = eda.d;
  const isStationary = eda.stationary;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 3</span>
        <h2 className="section-header mt-3">Data Preparation</h2>
        <p className="text-muted-foreground mt-1">
          Tahap ini mempersiapkan data sebelum modeling, termasuk transformasi dan uji stasioneritas.
        </p>
      </div>

      {/* Cleaning Info */}
      <div className="stat-card glow-border">
        <h3 className="text-sm font-semibold text-primary mb-2 flex items-center gap-2">
          <Beaker className="w-4 h-4" /> Proses Preparation
        </h3>

        <ul className="text-sm text-muted-foreground space-y-1">
          <li>• Penanganan missing values (interpolasi / forward fill)</li>
          <li>• Deteksi dan penyesuaian outlier</li>
          <li>• Transformasi untuk memastikan stasioneritas</li>
        </ul>

        <p className="text-xs text-muted-foreground mt-3 italic">
          Detail numerik cleaning belum tersedia dari backend.
        </p>
      </div>

      {/* Stationarity */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" /> Uji Stasioneritas (ADF)
        </h3>

        <div className="grid grid-cols-2 gap-4 text-center">
          <div>
            <div className={`text-xl font-bold font-mono ${isStationary ? "text-success" : "text-warning"}`}>
              {isStationary ? "Stasioner" : "Tidak Stasioner"}
            </div>
            <div className="text-xs text-muted-foreground">Status</div>
          </div>

          <div>
            <div className="text-xl font-bold font-mono text-primary">
              d = {dValue}
            </div>
            <div className="text-xs text-muted-foreground">Differencing Order</div>
          </div>
        </div>

        <div className={`mt-3 p-2 rounded text-xs text-center ${
          isStationary ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
        }`}>
          {isStationary
            ? `✓ Data sudah stasioner (d=${dValue})`
            : `⚠ Differencing diperlukan (d=${dValue})`}
        </div>
      </div>
    </div>
  );
};

export default DataPreparation;