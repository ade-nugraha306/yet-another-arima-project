import { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, Beaker, ArrowDownUp, Loader2 } from "lucide-react";
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

  const {
    d,
    stationary,
    adf_statistic,
    adf_p_value,
    missing_before,
    missing_after,
    outliers_before,
    outliers_after,
    cleaning_method,
  } = eda;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 3</span>
        <h2 className="section-header mt-3">Data Preparation & Cleaning</h2>
        <p className="text-muted-foreground mt-1">
          Membersihkan data dari missing values dan outlier, serta menguji stasioneritas.
        </p>
      </div>

      {/* Cleaning Method */}
      <div className="stat-card glow-border">
        <h3 className="text-sm font-semibold text-primary mb-2 flex items-center gap-2">
          <Beaker className="w-4 h-4" /> Metode Cleaning
        </h3>
        <p className="text-sm text-secondary-foreground font-mono bg-secondary/50 rounded p-3">
          {cleaning_method}
        </p>
      </div>

      {/* Missing Values & Outliers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" /> Missing Values
          </h3>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-destructive">{missing_before}</div>
              <div className="text-xs text-muted-foreground">Sebelum</div>
            </div>
            <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
            <div className="text-center">
              <div className="text-2xl font-bold text-success">{missing_after}</div>
              <div className="text-xs text-muted-foreground">Sesudah</div>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" /> Outliers
          </h3>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-destructive">{outliers_before}</div>
              <div className="text-xs text-muted-foreground">Sebelum</div>
            </div>
            <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
            <div className="text-center">
              <div className="text-2xl font-bold text-success">{outliers_after}</div>
              <div className="text-xs text-muted-foreground">Sesudah</div>
            </div>
          </div>
        </div>
      </div>

      {/* ADF Test */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" /> Augmented Dickey-Fuller Test
        </h3>

        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-xl font-bold font-mono text-foreground">{adf_statistic}</div>
            <div className="text-xs text-muted-foreground">ADF Statistic</div>
          </div>
          <div>
            <div className={`text-xl font-bold font-mono ${adf_p_value < 0.05 ? "text-success" : "text-warning"}`}>
              {adf_p_value}
            </div>
            <div className="text-xs text-muted-foreground">p-value</div>
          </div>
          <div>
            <div className="text-xl font-bold font-mono text-primary">d = {d}</div>
            <div className="text-xs text-muted-foreground">Differencing</div>
          </div>
        </div>

        <div className={`mt-3 p-2 rounded text-xs font-medium text-center ${
          stationary ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
        }`}>
          {stationary
            ? `✓ Data stasioner setelah differencing orde ${d} (p-value < 0.05)`
            : `⚠ Data tidak stasioner (p-value = ${adf_p_value})`}
        </div>
      </div>
    </div>
  );
};

export default DataPreparation;