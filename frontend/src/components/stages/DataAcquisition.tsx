// src/components/stages/DataAcquisition.tsx
import { useEffect, useState } from "react";
import { Database, FileSpreadsheet, Clock, Layers, Package, Loader2 } from "lucide-react";
import { getDataAcquisition, type DataAcquisitionResponse } from "@/services/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Props {
  family: string;
}

const DataAcquisition = ({ family }: Props) => {
  const [data, setData] = useState<DataAcquisitionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await getDataAcquisition(family);
        if (!cancelled) setData(res);
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Gagal memuat data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [family]);

  const infoCards = [
    { icon: FileSpreadsheet, label: "Sumber Data",    value: "Excel (.csv)" },
    { icon: Layers,          label: "Family",         value: family || "—" },
    { icon: Package,         label: "Jumlah SKU",     value: data ? `${data.sku_count} SKU` : "—" },
    { icon: Clock,           label: "Periode",        value: data ? `${data.total_weeks} Minggu` : "W1 – W40" },
    { icon: Database,        label: "Frekuensi",      value: "Weekly" },
  ];

  // Preview: first 5 rows
  const preview = data
    ? data.weeks.slice(0, 5).map((w, i) => ({ week: w, sales: data.sales_raw[i] }))
    : [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 2</span>
        <h2 className="section-header mt-3">Data Acquisition</h2>
        <p className="text-muted-foreground mt-1">
          Mengumpulkan dan memuat data penjualan mingguan dari sumber data Excel.
          Data diagregasi per <span className="text-primary font-semibold">Product Family</span>.
        </p>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {infoCards.map((c) => (
          <div key={c.label} className="stat-card text-center">
            <c.icon className="w-5 h-5 text-primary mx-auto mb-2" />
            <div className="text-sm text-muted-foreground">{c.label}</div>
            <div className="text-lg font-bold text-foreground">{c.value}</div>
          </div>
        ))}
      </div>

      {/* SKU list */}
      {data && data.skus.length > 0 && (
        <div className="stat-card">
          <h3 className="text-sm font-semibold text-primary mb-2">
            📦 SKU dalam Family <span className="text-foreground">{family}</span>
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.skus.map((sku) => (
              <span
                key={sku}
                className="text-xs px-2 py-1 rounded bg-primary/10 text-primary font-mono"
              >
                {sku}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Preview Table */}
      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">
          Preview Data (5 Baris Pertama — Sales Total Family)
        </h3>

        {loading && (
          <div className="flex items-center gap-2 text-muted-foreground text-sm py-4">
            <Loader2 className="w-4 h-4 animate-spin" /> Memuat data…
          </div>
        )}

        {error && (
          <p className="text-sm text-destructive py-2">{error}</p>
        )}

        {!loading && !error && preview.length === 0 && (
          <p className="text-sm text-muted-foreground py-2">Tidak ada data tersedia</p>
        )}

        {!loading && !error && preview.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>No</TableHead>
                    <TableHead>Tanggal (Minggu)</TableHead>
                    <TableHead>Total Sales Family</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.map((row, i) => (
                    <TableRow key={`${row.week}-${i}`}>
                      <TableCell>{i + 1}</TableCell>
                      <TableCell className="font-mono">{row.week}</TableCell>
                      <TableCell className="text-primary font-semibold">
                        {row.sales !== null ? row.sales.toLocaleString() : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <p className="text-xs text-muted-foreground mt-2">
              Menampilkan 5 dari {data?.total_weeks} total minggu.
              {" "}(Week 14 tidak tersedia dalam dataset — bukan missing data)
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default DataAcquisition;