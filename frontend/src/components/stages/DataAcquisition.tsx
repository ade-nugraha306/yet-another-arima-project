import { useEffect, useState } from "react";
import { Database, FileSpreadsheet, Clock, Layers, Loader2 } from "lucide-react";
import { getProducts, getEDA } from "@/services/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Props {
  product: string;
}

interface Row {
  week: string;
  sales: number;
}

const DataAcquisition = ({ product }: Props) => {
  const [productCount, setProductCount] = useState<number | null>(null);
  const [preview, setPreview] = useState<Row[]>([]);
  const [totalRows, setTotalRows] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const productsRes = await getProducts();
        const edaRes = await getEDA(product);

        console.log("PRODUCTS:", productsRes);
        console.log("EDA:", edaRes);

        if (cancelled) return;

        // ✅ Handle products safely
        setProductCount(productsRes.length);

        // ✅ Handle EDA safely (multi-format support)
        let rows: Row[] = [];

        if (edaRes?.dates && edaRes?.sales) {
          rows = edaRes.dates.map((d: string, i: number) => ({
            week: d,
            sales: edaRes.sales[i],
          }));
        }

        else if (Array.isArray(edaRes)) {
          // fallback kalau backend return array object
          rows = edaRes.map((r: any) => ({
            week: r.week ?? r.date ?? "-",
            sales: r.sales ?? r.value ?? 0,
          }));
        }

        else {
          console.warn("EDA shape tidak dikenali:", edaRes);
        }

        setTotalRows(rows.length);
        setPreview(rows.slice(0, 5));

      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Gagal memuat data");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [product]);

  const infoCards = [
    { icon: FileSpreadsheet, label: "Sumber Data", value: "Excel (.xlsx)" },
    { icon: Layers, label: "Jumlah Produk", value: productCount !== null ? `${productCount} Produk` : "—" },
    { icon: Clock, label: "Periode", value: "W1 – W40" },
    { icon: Database, label: "Frekuensi", value: "Weekly" },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <span className="section-badge">Tahap 2</span>
        <h2 className="section-header mt-3">Data Acquisition</h2>
        <p className="text-muted-foreground mt-1">
          Mengumpulkan dan memuat data penjualan mingguan dari sumber data Excel.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {infoCards.map((c) => (
          <div key={c.label} className="stat-card text-center">
            <c.icon className="w-5 h-5 text-primary mx-auto mb-2" />
            <div className="text-sm text-muted-foreground">{c.label}</div>
            <div className="text-lg font-bold text-foreground">{c.value}</div>
          </div>
        ))}
      </div>

      <div className="stat-card">
        <h3 className="text-sm font-semibold text-primary mb-3">
          Preview Data (5 Baris Pertama)
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
          <p className="text-sm text-muted-foreground py-2">
            Tidak ada data tersedia
          </p>
        )}

        {!loading && !error && preview.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>No</TableHead>
                    <TableHead>Minggu</TableHead>
                    <TableHead>Penjualan</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.map((row, i) => (
                    <TableRow key={`${row.week}-${i}`}>
                      <TableCell>{i + 1}</TableCell>
                      <TableCell>{row.week}</TableCell>
                      <TableCell className="text-primary font-semibold">
                        {row.sales}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <p className="text-xs text-muted-foreground mt-2">
              Menampilkan {preview.length} dari {totalRows} total record
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default DataAcquisition;