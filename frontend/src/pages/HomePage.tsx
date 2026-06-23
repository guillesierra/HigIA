import { Activity, AlertTriangle, Database, GitBranch, MapPinned } from "lucide-react";
import { useEffect, useState } from "react";
import { AlertsByYearChart } from "../charts/AlertsByYearChart";
import { RankingChart } from "../charts/RankingChart";
import { MetricStrip } from "../components/MetricStrip";
import { LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { ConsumptionRecord, SafetyAlert, Source, StudyDocument } from "../types/domain";

type HomePageProps = {
  onNavigate?: (route: string) => void;
};

export function HomePage({ onNavigate }: HomePageProps) {
  const [sources, setSources] = useState<Source[]>([]);
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [consumption, setConsumption] = useState<ConsumptionRecord[]>([]);
  const [studies, setStudies] = useState<StudyDocument[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.sources(), api.alerts(), api.consumption(), api.studies()])
      .then(([sourceRows, alertRows, consumptionRows, studyRows]) => {
        setSources(sourceRows);
        setAlerts(alertRows);
        setConsumption(consumptionRows);
        setStudies(studyRows);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const officialSources = sources.filter((source) => source.source_type.includes("official")).length;
  const geographies = new Set(consumption.map((row) => row.geography)).size;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Static public-data explorer</p>
          <h1>HigIA</h1>
          <p>
            Web estatica para explorar informacion publica sobre medicamentos, alertas sanitarias, consumo agregado,
            codigos ATC y documentacion relacionada con Asturias y Espana.
          </p>
        </div>
      </header>

      <MetricStrip
        metrics={[
          { label: "Fuentes", value: sources.length, tone: "teal" },
          { label: "Oficiales", value: officialSources, tone: "ink" },
          { label: "Alertas", value: alerts.length, tone: "rust" },
          { label: "Territorios", value: geographies, tone: "teal" }
        ]}
      />

      <section className="section-links" aria-label="Sections">
        {[
          ["Fuentes", "sources", <Database size={18} />],
          ["Alertas", "alerts", <AlertTriangle size={18} />],
          ["Consumo", "consumption", <Activity size={18} />],
          ["Relaciones", "relations", <GitBranch size={18} />],
          ["Asturias", "asturias", <MapPinned size={18} />]
        ].map(([label, route, icon]) => (
          <button key={String(route)} className="section-link" onClick={() => onNavigate?.(String(route))}>
            {icon}
            <span>{label}</span>
          </button>
        ))}
      </section>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Alertas por ano</h2>
          </div>
          <AlertsByYearChart alerts={alerts} />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Ranking por DHD</h2>
          </div>
          <RankingChart records={consumption} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Resumen de fuentes</h2>
        </div>
        <div className="source-summary">
          {sources.slice(0, 4).map((source) => (
            <div key={source.id}>
              <strong>{source.name}</strong>
              <span>{source.source_type}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

