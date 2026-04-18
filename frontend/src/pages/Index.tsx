// src/pages/Index.tsx
import { useEffect, useState } from "react";
import AppSidebar from "@/components/AppSidebar";
import BusinessUnderstanding from "@/components/stages/BusinessUnderstanding";
import DataAcquisition from "@/components/stages/DataAcquisition";
import DataPreparation from "@/components/stages/DataPreparation";
import EDA from "@/components/stages/EDA";
import Modeling from "@/components/stages/Modeling";
import Evaluation from "@/components/stages/Evaluation";
import { getProducts } from "@/services/api";

const Index = () => {
  const [activeStage, setActiveStage] = useState(0);
  const [productIndex, setProductIndex] = useState(0);
  const [horizon, setHorizon] = useState(5);

  // ── Daftar produk dari backend ───────────────────────────────
  const [products, setProducts] = useState<string[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);

  useEffect(() => {
    getProducts()
      .then((list) => {
        if (list.length > 0) {
          setProducts(list);
          setProductIndex(0);
        }
      })
      .catch(() => {
        // Backend belum jalan → fallback mock agar UI tidak crash
        console.warn("[Index] Backend tidak tersedia, menggunakan data mock.");
        setProducts(["Produk A", "Produk B", "Produk C"]);
      })
      .finally(() => setProductsLoading(false));
  }, []);

  // Selalu string valid, tidak pernah undefined
  const selectedProduct = products[productIndex] ?? products[0] ?? "";

  const renderStage = () => {
    switch (activeStage) {
      case 0: return <BusinessUnderstanding />;
      case 1: return <DataAcquisition product={selectedProduct} />
      case 2: return <DataPreparation product={selectedProduct} />;
      case 3: return <EDA product={selectedProduct} />;
      case 4:
        return (
          <Modeling
            productIndex={productIndex}
            selectedProduct={selectedProduct}
            horizon={horizon}
          />
        );
      case 5:
        return <Evaluation productIndex={productIndex} horizon={horizon} />;
      default:
        return <BusinessUnderstanding />;
    }
  };

  return (
    <div className="flex min-h-screen w-full bg-background">
      <AppSidebar
        activeStage={activeStage}
        onStageChange={setActiveStage}
        productIndex={productIndex}
        onProductChange={setProductIndex}
        horizon={horizon}
        onHorizonChange={setHorizon}
        products={products}
        productsLoading={productsLoading}
      />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-6 md:p-8">
          {productsLoading ? (
            <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
              <span className="animate-pulse">Memuat data produk dari backend…</span>
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