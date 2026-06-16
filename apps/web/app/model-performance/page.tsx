import PlaceholderPanel from "@/components/PlaceholderPanel";

export default function ModelPerformancePage() {
  return (
    <PlaceholderPanel
      title="Model Performance"
      sprint="Sprint 6"
      description="Model evaluation dashboard showing RMSE, MAE, SMAPE, bias,
        and prediction interval coverage per model version. Walk-forward
        cross-validation results across product categories and stores.
        WRMSSE metric aligned with M5 competition methodology."
    />
  );
}
