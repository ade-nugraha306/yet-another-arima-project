// src/components/AppSidebar.tsx
import { useState } from "react";
import {
  BarChart3, ChevronLeft, ChevronRight, Play,
  Database, Brain, Search, ClipboardCheck, Settings, LineChart
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";

const stages = [
  { id: 0, label: "Business Understanding", icon: ClipboardCheck },
  { id: 1, label: "Data Acquisition",       icon: Database },
  { id: 2, label: "Data Preparation",       icon: Settings },
  { id: 3, label: "EDA",                    icon: Search },
  { id: 4, label: "Modeling",               icon: Brain },
  { id: 5, label: "Evaluation",             icon: LineChart },
];

interface Props {
  activeStage: number;
  onStageChange: (stage: number) => void;
  familyIndex: number;
  onFamilyChange: (idx: number) => void;
  horizon: number;
  onHorizonChange: (h: number) => void;
  families: string[];
  familiesLoading: boolean;
}

const AppSidebar = ({
  activeStage, onStageChange,
  familyIndex, onFamilyChange,
  horizon, onHorizonChange,
  families, familiesLoading,
}: Props) => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`h-screen sticky top-0 flex flex-col border-r border-border bg-sidebar transition-all duration-300 ${collapsed ? "w-16" : "w-72"}`}>

      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-sidebar-border">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-primary" />
            <span className="font-bold text-sm text-sidebar-foreground">ARIMA Forecaster</span>
          </div>
        )}
        {collapsed && <BarChart3 className="w-6 h-6 text-primary mx-auto" />}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-muted-foreground hover:text-foreground"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Stage Navigation */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {!collapsed && (
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground px-2 py-2">
            Data Science Life Cycle
          </div>
        )}
        {stages.map((s) => (
          <button
            key={s.id}
            onClick={() => onStageChange(s.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
              activeStage === s.id
                ? "bg-primary/15 text-primary font-semibold"
                : "text-sidebar-foreground hover:bg-sidebar-accent"
            }`}
          >
            <s.icon className="w-4 h-4 shrink-0" />
            {!collapsed && <span className="truncate">{s.label}</span>}
          </button>
        ))}
      </div>

      {/* Controls */}
      {!collapsed && (
        <div className="p-4 border-t border-sidebar-border space-y-4">

          {/* Family selector */}
          <div>
            <Label className="text-xs text-muted-foreground">Product Family</Label>
            {familiesLoading ? (
              <div className="mt-1 h-9 rounded-md bg-sidebar-accent border border-sidebar-border animate-pulse" />
            ) : (
              <Select
                value={String(familyIndex)}
                onValueChange={(v) => onFamilyChange(Number(v))}
              >
                <SelectTrigger className="mt-1 bg-sidebar-accent border-sidebar-border text-sm">
                  <SelectValue placeholder="Pilih family…" />
                </SelectTrigger>
                <SelectContent className="max-h-60">
                  {families.map((f, i) => (
                    <SelectItem key={i} value={String(i)}>
                      {f}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Horizon slider */}
          <div>
            <Label className="text-xs text-muted-foreground">
              Forecast Horizon: {horizon} minggu
            </Label>
            <Slider
              value={[horizon]}
              onValueChange={(v) => onHorizonChange(v[0])}
              min={1}
              max={12}
              step={1}
              className="mt-2"
            />
          </div>

          <Button
            className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
            size="sm"
          >
            <Play className="w-3.5 h-3.5 mr-2" />
            Run Model
          </Button>
        </div>
      )}
    </div>
  );
};

export default AppSidebar;