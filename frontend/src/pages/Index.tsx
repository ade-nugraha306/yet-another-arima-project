// src/pages/Index.tsx
import { useEffect, useState } from "react";
import AppSidebar from "@/components/AppSidebar";
import BusinessUnderstanding from "@/components/stages/BusinessUnderstanding";
import DataAcquisition from "@/components/stages/DataAcquisition";
import DataPreparation from "@/components/stages/DataPreparation";
import EDA from "@/components/stages/EDA";
import Modeling from "@/components/stages/Modeling";
import Evaluation from "@/components/stages/Evaluation";
import { getFamilies } from "@/services/api";

const Index = () => {
  const [activeStage, setActiveStage] = useState(0);
  const [familyIndex, setFamilyIndex] = useState(0);
  const [horizon, setHorizon] = useState(5);

  // ── Daftar family dari backend ───────────────────────────────
  const [families, setFamilies] = useState<string[]>([]);
  const [familiesLoading, setFamiliesLoading] = useState(true);

  useEffect(() => {
    getFamilies()
      .then((list) => {
        if (list.length > 0) {
          setFamilies(list);
          setFamilyIndex(0);
        }
      })
      .catch(() => {
        console.warn("[Index] Backend tidak tersedia, menggunakan mock families.");
        setFamilies(["5DAYS", "CAF", "FOX", "HYDROPLUS", "TUBRUK", "UHT"]);
      })
      .finally(() => setFamiliesLoading(false));
  }, []);

  const selectedFamily = families[familyIndex] ?? families[0] ?? "";

  const renderStage = () => {
    switch (activeStage) {
      case 0: return <BusinessUnderstanding />;
      case 1: return <DataAcquisition family={selectedFamily} />;
      case 2: return <DataPreparation family={selectedFamily} />;
      case 3: return <EDA family={selectedFamily} />;
      case 4:
        return (
          <Modeling
            selectedFamily={selectedFamily}
            horizon={horizon}
          />
        );
      case 5:
        return <Evaluation family={selectedFamily} />;
      default:
        return <BusinessUnderstanding />;
    }
  };

  return (
    <div className="flex min-h-screen w-full bg-background">
      <AppSidebar
        activeStage={activeStage}
        onStageChange={setActiveStage}
        familyIndex={familyIndex}
        onFamilyChange={setFamilyIndex}
        horizon={horizon}
        onHorizonChange={setHorizon}
        families={families}
        familiesLoading={familiesLoading}
      />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-6 md:p-8">
          {familiesLoading ? (
            <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
              <span className="animate-pulse">Memuat daftar family dari backend…</span>
            </div>
          ) : (
            renderStage()
          )}
        </div>
      </main>
    </div>
  );
};

export default Index;