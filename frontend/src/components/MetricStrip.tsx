type Metric = {
  label: string;
  value: string | number;
  tone?: "teal" | "rust" | "ink";
};

export function MetricStrip({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="metric-strip">
      {metrics.map((metric) => (
        <div className={`metric ${metric.tone ?? "ink"}`} key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
        </div>
      ))}
    </div>
  );
}

