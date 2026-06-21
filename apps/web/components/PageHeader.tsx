interface PageHeaderProps {
  title: string;
  subtitle: string;
  kicker?: string;
  badge?: string;
}

export default function PageHeader({
  title,
  subtitle,
  kicker = "DemandOS workspace",
  badge = "Synthetic data · no external actions",
}: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        <div className="page-kicker">{kicker}</div>
        <h1 className="page-title">{title}</h1>
        <p className="page-subtitle">{subtitle}</p>
      </div>
      {badge && <div className="page-badge">{badge}</div>}
    </header>
  );
}
