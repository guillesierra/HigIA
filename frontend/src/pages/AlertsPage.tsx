import { AlertTriangle, ExternalLink, Info, Tag } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AlertsByYearChart } from "../charts/AlertsByYearChart";
import { AlertTable } from "../components/AlertTable";
import { FilterPanel } from "../components/FilterPanel";
import { LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { SafetyAlert } from "../types/domain";

const THERAPEUTIC_TAGS: Record<string, string> = {
  antibiotic: "Antibióticos",
  nsaid: "AINEs",
  opioid: "Opioides",
  benzodiazepine: "Benzodiacepinas",
  antidepressant: "Antidepresivos",
  statin: "Estatinas",
  ppi: "IBPs",
  anticoagulant: "Anticoagulantes",
  antidiabetic: "Antidiabéticos",
  antihypertensive: "Antihipertensivos",
  antipsychotic: "Antipsicóticos",
  antineoplastic: "Antineoplásicos",
};

export function AlertsPage() {
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [year, setYear] = useState("");
  const [medicine, setMedicine] = useState("");
  const [atc, setAtc] = useState("");
  const [category, setCategory] = useState("");
  const [selected, setSelected] = useState<SafetyAlert | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.alerts().then((rows) => {
      setAlerts(rows);
      setSelected(rows[0] ?? null);
    }).finally(() => setLoading(false));
  }, []);

  const rows = useMemo(() =>
    alerts.filter((alert) => {
      const text = `${alert.title} ${alert.summary ?? ""} ${alert.raw_text ?? ""} ${(alert.possible_active_ingredients ?? []).join(" ")}`.toLowerCase();
      if (year && alert.date?.slice(0, 4) !== year) return false;
      if (medicine && !text.includes(medicine.toLowerCase())) return false;
      if (atc && !text.includes(atc.toLowerCase())) return false;
      if (category) {
        const catLower = category.toLowerCase();
        const hasCat = Object.entries(THERAPEUTIC_TAGS).some(([key, label]) =>
          key.includes(catLower) && (text.includes(key) || text.includes(label.toLowerCase()))
        );
        if (!hasCat) return false;
      }
      return true;
    }),
    [alerts, year, medicine, atc, category]
  );

  const years = useMemo(() => {
    const yrs = new Set<string>();
    alerts.forEach((a) => { if (a.date) yrs.add(a.date.slice(0, 4)); });
    return Array.from(yrs).sort().reverse();
  }, [alerts]);

  const categories = useMemo(() => {
    const cats = new Set<string>();
    alerts.forEach((a) => {
      const text = `${a.title} ${a.summary ?? ""} ${a.raw_text ?? ""}`.toLowerCase();
      Object.entries(THERAPEUTIC_TAGS).forEach(([key, label]) => {
        if (text.includes(key)) cats.add(label);
      });
    });
    return Array.from(cats).sort();
  }, [alerts]);

  const stats = useMemo(() => {
    const orgs = new Map<string, number>();
    rows.forEach((a) => {
      const org = a.organization ?? "Desconocido";
      orgs.set(org, (orgs.get(org) ?? 0) + 1);
    });
    const detectedIngredients = rows.filter((a) => (a.possible_active_ingredients?.length ?? 0) > 0).length;
    return { orgCounts: Array.from(orgs.entries()).sort((a, b) => b[1] - a[1]), withIngredients: detectedIngredients };
  }, [rows]);

  if (loading) return <LoadingState />;

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">AEMPS y otras fuentes</p>
          <h1>Alertas de seguridad de medicamentos</h1>
          <p className="muted">
            Notas informativas y alertas de farmacovigilancia emitidas por la Agencia Española de Medicamentos (AEMPS).
            Cada alerta advierte sobre riesgos, retiradas o cambios en las condiciones de uso de medicamentos.
          </p>
          <p className="muted" style={{ marginTop: 4 }}>
            {rows.length} alertas filtradas de {alerts.length} totales | {stats.withIngredients} con principios activos detectados
          </p>
        </div>
      </header>

      <FilterPanel>
        <select value={year} onChange={(event) => setYear(event.target.value)}>
          <option value="">Todos los años</option>
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
        <input value={medicine} onChange={(event) => setMedicine(event.target.value)} placeholder="Medicamento o principio activo" />
        <input value={atc} onChange={(event) => setAtc(event.target.value)} placeholder="Código ATC" />
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="">Todas las categorías</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </FilterPanel>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Distribución anual de alertas</h2>
            <p className="muted">Número de alertas de seguridad emitidas por año</p>
          </div>
          <AlertsByYearChart alerts={rows} />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Detalle de la alerta</h2>
            <p className="muted">Información sobre la alerta seleccionada</p>
          </div>
          {selected ? (
            <div className="detail">
              <strong>{selected.title}</strong>
              <span>{selected.date ?? "Fecha no disponible"} | {selected.organization ?? "AEMPS"}</span>
              <span><Tag size={12} /> {selected.alert_type ?? "Seguridad"}</span>
              <div className="detail-info">
                <Info size={14} />
                <span>Esta alerta informa sobre riesgos de seguridad, cambios en la ficha técnica o nuevas contraindicaciones de medicamentos.</span>
              </div>
              <p>{selected.summary ?? "Sin resumen estructurado. Consulte la fuente original para más detalles."}</p>
              {selected.possible_active_ingredients?.length ? (
                <div>
                  <p style={{ marginBottom: 4, fontWeight: 600 }}>Principios activos detectados:</p>
                  <div className="tags">
                    {selected.possible_active_ingredients.map((ing) => (
                      <span key={ing} className="tag">{ing}</span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="muted">No se detectaron principios activos específicos en esta alerta.</p>
              )}
              <a href={selected.url} target="_blank" rel="noreferrer">
                Ver fuente original (AEMPS) <ExternalLink size={14} />
              </a>
            </div>
          ) : (
            <p className="muted">Selecciona una alerta de la tabla inferior para ver el detalle.</p>
          )}
        </div>
      </section>

      <section className="panel" style={{ marginTop: 16 }}>
        <div className="panel-heading"><h2>Alertas por organismo emisor</h2></div>
        <div className="grid four" style={{ padding: 12 }}>
          {stats.orgCounts.map(([org, count]) => (
            <div key={org} className="mini-card">
              <span className="mini-value">{count}</span>
              <span className="mini-label">{org}</span>
            </div>
          ))}
        </div>
      </section>

      <AlertTable alerts={rows} selectedId={selected?.id} onSelect={setSelected} />
    </div>
  );
}
