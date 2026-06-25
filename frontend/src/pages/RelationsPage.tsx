import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ConsumptionChart } from "../components/ConsumptionChart";
import { AlertTable } from "../components/AlertTable";
import { RelationshipGraph } from "../components/RelationshipGraph";
import { StudyCard } from "../components/StudyCard";
import { EmptyState, LoadingState } from "../components/Status";
import { api } from "../services/api";
import { getAtcName } from "../services/labels";
import type { ATCCode, Drug, RelationshipResponse, SafetyAlert } from "../types/domain";

export function RelationsPage() {
  const [kind, setKind] = useState<"atc" | "drug" | "alert">("atc");
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [atcCodes, setAtcCodes] = useState<ATCCode[]>([]);
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [result, setResult] = useState<RelationshipResponse | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<SafetyAlert | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedQuery, setSelectedQuery] = useState("");
  const [searchFilter, setSearchFilter] = useState("");

  useEffect(() => {
    Promise.all([api.drugs(), api.atc(), api.alerts()])
      .then(([d, a, al]) => { setDrugs(d); setAtcCodes(a); setAlerts(al); })
      .finally(() => setLoading(false));
  }, []);

  const topItems = useMemo(() => {
    if (kind === "atc") {
      const unique = new Map<string, ATCCode>();
      atcCodes.forEach(a => { if (!unique.has(a.code)) unique.set(a.code, a); });
      return Array.from(unique.values());
    }
    if (kind === "drug") return drugs.filter(d => d.active_ingredient);
    if (kind === "alert") return alerts.filter(a => a.date).sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));
    return [];
  }, [kind, atcCodes, drugs, alerts]);

  const search = (query: string) => {
    if (!query) return;
    setSelectedQuery(query);
    setSearchLoading(true);
    api.relationship(kind, query)
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
          <p className="muted">Explora conexiones entre medicamentos, códigos ATC, alertas y datos de consumo. Haz clic en cualquier elemento para ver sus relaciones.</p>
        </div>
      </header>

      {/* TYPE SELECTOR */}
      <div className="section-links" style={{ marginBottom: 8 }}>
        {[
          ["ATC", "atc"],
          ["Medicamentos", "drug"],
          ["Alertas", "alert"],
        ].map(([label, id]) => (
          <button key={id} className={`section-link ${kind === id ? "active-link" : ""}`}
            onClick={() => { setKind(id as typeof kind); setResult(null); setSelectedQuery(""); }}>
            {label}
          </button>
        ))}
      </div>

      {/* GRID OF AVAILABLE ITEMS */}
      {!result && (
        <section className="panel">
          <div className="panel-heading">
            <h2>{kind === "atc" ? `${atcCodes.length} códigos ATC` : kind === "drug" ? `${drugs.length} medicamentos` : `${alerts.length} alertas`}</h2>
            <p className="muted">Haz clic para ver relaciones. Escribe para filtrar.</p>
          </div>
          <input
            className="curve-search"
            type="text"
            placeholder="Filtrar…"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            style={{ margin: "0 12px 8px", width: "calc(100% - 24px)", minHeight: 34 }}
          />
          <div className="relations-grid" style={{ maxHeight: 500, overflow: "auto" }}>
            {kind === "atc" && (topItems as ATCCode[])
              .filter(item => !searchFilter || item.code.toLowerCase().includes(searchFilter.toLowerCase()) || item.name.toLowerCase().includes(searchFilter.toLowerCase()))
              .slice(0, 200).map((item) => (
              <button key={item.code} className={`relation-card ${selectedQuery === item.code ? "selected" : ""}`}
                onClick={() => search(item.code)}>
                <strong>{item.code}</strong>
                <span>{item.name}</span>
              </button>
            ))}
            {kind === "drug" && (topItems as Drug[])
              .filter(item => !searchFilter || item.name.toLowerCase().includes(searchFilter.toLowerCase()) || (item.active_ingredient || "").toLowerCase().includes(searchFilter.toLowerCase()))
              .slice(0, 200).map((item) => (
              <button key={item.id} className={`relation-card ${selectedQuery === item.name ? "selected" : ""}`}
                onClick={() => search(item.name)}>
                <strong>{item.name}</strong>
                <span>{item.active_ingredient || item.normalized_name}</span>
              </button>
            ))}
            {kind === "alert" && (topItems as SafetyAlert[])
              .filter(item => !searchFilter || item.title.toLowerCase().includes(searchFilter.toLowerCase()))
              .slice(0, 200).map((item) => (
              <button key={item.id} className={`relation-card ${selectedQuery === String(item.id) ? "selected" : ""}`}
                onClick={() => search(String(item.id))}>
                <strong>{item.date?.slice(0, 10) ?? "—"}</strong>
                <span>{item.title.slice(0, 80)}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {searchLoading && <LoadingState />}

      {/* RESULTS */}
      {result && (
        <>
          <div className="section-links" style={{ marginBottom: 12 }}>
            <button className="text-button" onClick={() => { setResult(null); setSelectedQuery(""); }}>
              ← Volver a la lista
            </button>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Relaciones de: {selectedQuery}</h2>
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
                {result.studies.length ? result.studies.map((s) => <StudyCard key={s.id} study={s} />) : <EmptyState message="No hay estudios relacionados." />}
              </div>
            </div>
          </section>

          <AlertTable alerts={result.alerts} selectedId={selectedAlert?.id} onSelect={setSelectedAlert} />
        </>
      )}
    </div>
  );
}
