import PlaceholderPanel from "@/components/PlaceholderPanel";

export default function ForecastsPage() {
  return (
    <PlaceholderPanel
      title="Forecast Explorer"
      sprint="Sprint 4"
      description="The 28-day demand forecast for every SKU/store combination.
        Includes point forecasts, 90% prediction intervals, and comparison
        against naive seasonal baseline. Filter by product, category, or store.
        Charts powered by Recharts."
    />
  );
}
