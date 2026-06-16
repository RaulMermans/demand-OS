import PlaceholderPanel from "@/components/PlaceholderPanel";

export default function DataHealthPage() {
  return (
    <PlaceholderPanel
      title="Data Health"
      sprint="Sprint 1"
      description="Validation report for ingested raw records. Shows: missing
        product/store references, negative quantities, future-dated orders,
        duplicate records, schema drift alerts, and connector run history.
        This is the first page to go live after Sprint 1 ingestion."
    />
  );
}
