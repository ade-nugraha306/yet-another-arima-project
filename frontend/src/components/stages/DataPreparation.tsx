import { CheckCircle2, AlertTriangle, Beaker, ArrowDownUp } from "lucide-react";
import { getCleaningStats } from "@/lib/mockData";

const DataPreparation = () => {
  const stats = getCleaningStats();

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 3</span>
        <h2 className="section-header mt-3">Data Preparation & Cleaning</h2>
        <p className="text-muted-foreground mt-1">
          Membersihkan data dari missing values dan outlier, serta menguji stasioneritas.
        </p>
      </div>

      <div className="stat-card glow-border">
        <h3 className="text-sm font-semibold text-primary mb-2 flex items-center gap-2">
          <Beaker className="w-4 h-4" /> Metode Cleaning
        </h3>
        <p className="text-sm text-secondary-foreground font-mono bg-secondary/50 rounded p-3">
          {stats.method}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" /> Missing Values
          </h3>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-destructive">{stats.missingBefore}</div>
              <div className="text-xs text-muted-foreground">Sebelum</div>
            </div>
            <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
            <div className="text-center">
              <div className="text-2xl font-bold text-success">{stats.missingAfter}</div>
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
              <div className="text-2xl font-bold text-destructive">{stats.outliersBefore}</div>
              <div className="text-xs text-muted-foreground">Sebelum</div>
            </div>
            <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
            <div className="text-center">
              <div className="text-2xl font-bold text-success">{stats.outliersAfter}</div>
              <div className="text-xs text-muted-foreground">Sesudah</div>
            </div>
          </div>
        </div>
      </div>

      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" /> Augmented Dickey-Fuller Test
        </h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-xl font-bold font-mono text-foreground">{stats.adfStatistic}</div>
            <div className="text-xs text-muted-foreground">ADF Statistic</div>
          </div>
          <div>
            <div className="text-xl font-bold font-mono text-success">{stats.adfPValue}</div>
            <div className="text-xs text-muted-foreground">p-value</div>
          </div>
          <div>
            <div className="text-xl font-bold font-mono text-primary">d = {stats.dValue}</div>
            <div className="text-xs text-muted-foreground">Differencing</div>
          </div>
        </div>
        <div className="mt-3 p-2 rounded bg-success/10 text-success text-xs font-medium text-center">
          ✓ Data stasioner setelah differencing orde {stats.dValue} (p-value &lt; 0.05)
        </div>
      </div>
    </div>
  );
};

export default DataPreparation;
