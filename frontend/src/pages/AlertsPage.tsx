import { ExternalLink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AlertsByYearChart } from "../charts/AlertsByYearChart";
import { AlertTable } from "../components/AlertTable";
import { FilterPanel } from "../components/FilterPanel";
import { LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { SafetyAlert } from "../types/domain";

export function AlertsPage() {
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [year, setYear] = useState("");
  const [medicine, setMedicine] = useState("");
  const [atc, setAtc] = useState("");
  const [selected, setSelected] = useState<SafetyAlert | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.alerts().then((rows) => {
      setAlerts(rows);
      setSelected(rows[0] ?? null);
    }).finally(() => setLoading(false));
  }, []);

  const rows = useMemo(
    () =>
      alerts.filter((alert) => {
        const text = `${alert.title} ${alert.summary ?? ""} ${alert.raw_text ?? ""} ${(alert.possible_active_ingredients ?? []).join(" ")}`.toLowerCase();
        if (year && alert.date?.slice(0, 4) !== year) return false;
        if (medicine && !text.includes(medicine.toLowerCase())) return false;
        if (atc && !text.includes(atc.toLowerCase())) return false;
        return true;
      }),
    [alerts, year, medicine, atc]
  );

  if (loading) return <LoadingState />;

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">AEMPS</p>
          <h1>Alertas</h1>
        </div>
      </header>

      <FilterPanel>
        <input value={year} onChange={(event) => setYear(event.target.value)} placeholder="Ano" inputMode="numeric" />
        <input value={medicine} onChange={(event) => setMedicine(event.target.value)} placeholder="Medicamento o principio activo" />
        <input value={atc} onChange={(event) => setAtc(event.target.value)} placeholder="ATC" />
      </FilterPanel>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Distribucion anual</h2>
          </div>
          <AlertsByYearChart alerts={rows} />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Detalle</h2>
          </div>
          {selected ? (
            <div className="detail">
              <strong>{selected.title}</strong>
              <span>{selected.date ?? "Fecha no disponible"}</span>
              <p>{selected.summary ?? "Sin resumen estructurado."}</p>
              {selected.possible_active_ingredients?.length ? <p>Principios detectados: {selected.possible_active_ingredients.join(", ")}</p> : null}
              <a href={selected.url} target="_blank" rel="noreferrer">
                Fuente original <ExternalLink size={14} />
              </a>
            </div>
          ) : (
            <p className="muted">Selecciona una alerta para ver el detalle.</p>
          )}
        </div>
      </section>

      <AlertTable alerts={rows} selectedId={selected?.id} onSelect={setSelected} />
    </div>
  );
}

