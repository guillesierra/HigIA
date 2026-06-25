import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ConsumptionChart } from "../components/ConsumptionChart";
import { AlertTable } from "../components/AlertTable";
import { FilterPanel } from "../components/FilterPanel";
import { RelationshipGraph } from "../components/RelationshipGraph";
import { StudyCard } from "../components/StudyCard";
import { EmptyState, LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { ATCCode, Drug, RelationshipResponse, SafetyAlert } from "../types/domain";

export function RelationsPage() {
  const [kind, setKind] = useState<"drug" | "atc" | "alert">("atc");
  const [query, setQuery] = useState("");
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [atcCodes, setAtcCodes] = useState<ATCCode[]>([]);
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [result, setResult] = useState<RelationshipResponse | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<SafetyAlert | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);

  useEffect(() => {
    Promise.all([api.drugs(), api.atc(), api.alerts()])
      .then(([d, a, al]) => { setDrugs(d); setAtcCodes(a); setAlerts(al); })
      .finally(() => setLoading(false));
  }, []);

  const options = useMemo(() => {
    if (kind === "atc") return atcCodes.map(a => ({ value: a.code, label: `${a.code} — ${a.name}` }));
    if (kind === "drug") return drugs.filter(d => d.normalized_name).slice(0, 200).map(d => ({ value: d.name, label: `${d.name}${d.active_ingredient ? ` (${d.active_ingredient})` : ""}` }));
    if (kind === "alert") return alerts.slice(0, 100).map(a => ({ value: String(a.id), label: `${a.date?.slice(0,10) ?? "?"} — ${a.title.slice(0, 80)}` }));
    return [];
  }, [kind, atcCodes, drugs, alerts]);

  // Filter options by search text
  const filteredOptions = useMemo(() => {
    if (!query) return options.slice(0, 50);
    const q = query.toLowerCase();
    return options.filter(o => o.label.toLowerCase().includes(q)).slice(0, 50);
  }, [options, query]);

  const search = (val?: string) => {
    const q = val || query;
    if (!q) return;
    setSearchLoading(true);
    api.relationship(kind, q)
      .then((value) => { setResult(value); setSelectedAlert(value.alerts[0] ?? null); })
      .finally(() => setSearchLoading(false));
  };

  if (loading) return <LoadingState />;

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Vista vinculada</p>
          <h1>Relaciones</h1>
          <p className="muted">Explora conexiones entre medicamentos, códigos ATC, alertas de seguridad y datos de consumo.</p>
        </div>
      </header>

      <FilterPanel
        actions={
          <button className="primary-button" type="button" onClick={() => search()} disabled={!query}>
            <Search size={16} />
            Buscar
          </button>
        }
      >
        <select value={kind} onChange={(e) => { setKind(e.target.value as typeof kind); setQuery(""); setResult(null); }}>
          <option value="atc">Código ATC</option>
          <option value="drug">Medicamento</option>
          <option value="alert">Alerta</option>
        </select>
        <div style={{ position: "relative", flex: 1, minWidth: 300 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={kind === "atc" ? "Escribe o selecciona un código ATC…" : kind === "drug" ? "Escribe o selecciona un medicamento…" : "Escribe o selecciona una alerta…"}
            style={{ width: "100%" }}
          />
          {query && filteredOptions.length > 0 && (
            <div className="autocomplete-dropdown">
              {filteredOptions.map((opt) => (
                <button
                  key={opt.value}
                  className="autocomplete-item"
                  onClick={() => { setQuery(opt.value); search(opt.value); }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </FilterPanel>

      {searchLoading && <LoadingState />}
      {!searchLoading && !result && <EmptyState message={kind === "atc" ? "Selecciona un código ATC para ver sus relaciones." : kind === "drug" ? "Selecciona un medicamento para ver sus relaciones." : "Selecciona una alerta para ver sus relaciones."} />}
      {result && (
        <>
          <section className="panel">
            <div className="panel-heading">
              <h2>Grafo de relaciones — {result.query}</h2>
            </div>
            <RelationshipGraph result={result} />
          </section>

          <section className="grid two">
            <div className="panel">
              <div className="panel-heading"><h2>Consumo relacionado</h2></div>
              <ConsumptionChart records={result.consumption} />
            </div>
            <div className="panel">
              <div className="panel-heading"><h2>Estudios y documentos</h2></div>
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
