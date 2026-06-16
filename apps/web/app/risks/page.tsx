import PlaceholderPanel from "@/components/PlaceholderPanel";

export default function RisksPage() {
  return (
    <PlaceholderPanel
      title="Inventory Risk"
      sprint="Sprint 5"
      description="Stockout risk heatmap across all SKU/store combinations.
        Risk tiers: Critical (stockout within lead time), High, Medium, Low.
        Computed from forecasted demand, current inventory, and supplier lead times.
        No hardcoded values — all scores are computed by StockoutService."
    />
  );
}
