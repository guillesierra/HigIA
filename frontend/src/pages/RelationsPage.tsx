import { Search } from "lucide-react";
import { useState } from "react";
import { ConsumptionChart } from "../components/ConsumptionChart";
import { AlertTable } from "../components/AlertTable";
import { FilterPanel } from "../components/FilterPanel";
import { RelationshipGraph } from "../components/RelationshipGraph";
import { StudyCard } from "../components/StudyCard";
import { EmptyState, LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { RelationshipResponse, SafetyAlert } from "../types/domain";

export function RelationsPage() {
  const [kind, setKind] = useState<"drug" | "atc" | "alert">("drug");
  const [query, setQuery] = useState("amoxicillin");
  const [result, setResult] = useState<RelationshipResponse | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<SafetyAlert | null>(null);
  const [loading, setLoading] = useState(false);

  const search = () => {
    setLoading(true);
    api.relationship(kind, query)
      .then((value) => {
        setResult(value);
        setSelectedAlert(value.alerts[0] ?? null);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Linked view</p>
          <h1>Relaciones</h1>
        </div>
      </header>

      <FilterPanel
        actions={
          <button className="primary-button" type="button" onClick={search}>
            <Search size={16} />
            Buscar
          </button>
        }
      >
        <select value={kind} onChange={(event) => setKind(event.target.value as "drug" | "atc" | "alert")}>
          <option value="drug">Medicamento</option>
          <option value="atc">ATC</option>
          <option value="alert">Alerta</option>
        </select>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Medicamento o ATC" />
      </FilterPanel>

      {loading && <LoadingState />}
      {!loading && !result && <EmptyState message="Busca un medicamento o codigo ATC para ver relaciones." />}
      {result && (
        <>
          <section className="panel">
            <div className="panel-heading">
              <h2>Grafo de relaciones</h2>
            </div>
            <RelationshipGraph result={result} />
          </section>

          <section className="grid two">
            <div className="panel">
              <div className="panel-heading">
                <h2>Consumo relacionado</h2>
              </div>
              <ConsumptionChart records={result.consumption} />
            </div>
            <div className="panel">
              <div className="panel-heading">
                <h2>Estudios y documentos</h2>
              </div>
              <div className="study-list">
                {result.studies.length ? result.studies.map((study) => <StudyCard study={study} key={study.id} />) : <EmptyState message="No hay estudios relacionados." />}
              </div>
            </div>
          </section>

          <AlertTable alerts={result.alerts} selectedId={selectedAlert?.id} onSelect={setSelectedAlert} />
        </>
      )}
    </div>
  );
}

