import { Database, FileSpreadsheet, Clock, Layers } from "lucide-react";
import { generateWeeklyData } from "@/lib/mockData";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Props {
  productIndex: number;
}

const DataAcquisition = ({ productIndex }: Props) => {
  const data = generateWeeklyData(productIndex);
  const preview = data.slice(0, 5);

  const infoCards = [
    { icon: FileSpreadsheet, label: "Sumber Data", value: "Excel (.xlsx)" },
    { icon: Layers, label: "Jumlah Produk", value: "4 Produk" },
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
        <h3 className="text-sm font-semibold text-primary mb-3">Preview Data (5 Baris Pertama)</h3>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-muted-foreground">No</TableHead>
                <TableHead className="text-muted-foreground">Minggu</TableHead>
                <TableHead className="text-muted-foreground">Penjualan</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {preview.map((row, i) => (
                <TableRow key={row.week}>
                  <TableCell className="font-mono text-sm">{i + 1}</TableCell>
                  <TableCell className="font-mono text-sm">{row.week}</TableCell>
                  <TableCell className="font-mono text-sm text-primary font-semibold">{row.sales}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Menampilkan {preview.length} dari {data.length} total record
        </p>
      </div>
    </div>
  );
};

export default DataAcquisition;
