import type { RelationshipResponse } from "../types/domain";

export function RelationshipGraph({ result }: { result: RelationshipResponse }) {
  const nodes = [
    { label: "Medicamentos", value: result.drugs.length, tone: "teal" },
    { label: "ATC", value: result.atc_codes.length, tone: "ink" },
    { label: "Alertas", value: result.alerts.length, tone: "rust" },
    { label: "Consumo", value: result.consumption.length, tone: "teal" },
    { label: "Estudios", value: result.studies.length, tone: "ink" }
  ];

  return (
    <div className="relationship-graph" aria-label="Relationship graph">
      {nodes.map((node, index) => (
        <div className="graph-step" key={node.label}>
          <div className={`graph-node ${node.tone}`}>
            <strong>{node.value}</strong>
            <span>{node.label}</span>
          </div>
          {index < nodes.length - 1 ? <div className="graph-edge" /> : null}
        </div>
      ))}
    </div>
  );
}

