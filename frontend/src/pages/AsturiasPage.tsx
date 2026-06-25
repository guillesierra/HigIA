import { TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { TimeSeriesChart } from "../charts/TimeSeriesChart";
import { MetricStrip } from "../components/MetricStrip";
import { StudyCard } from "../components/StudyCard";
import { EmptyState, LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { ConsumptionRecord, Source, StudyDocument } from "../types/domain";

export function AsturiasPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [studies, setStudies] = useState<StudyDocument[]>([]);
  const [consumption, setConsumption] = useState<ConsumptionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.sources(), api.studies(), api.consumption()])
      .then(([s, st, c]) => { setSources(s); setStudies(st); setConsumption(c); })
      .finally(() => setLoading(false));
  }, []);

  const asturiasSources = useMemo(() => sources.filter((s) => `${s.name} ${s.url}`.toLowerCase().includes("astur")), [sources]);
  const asturiasStudies = useMemo(() => studies.filter((s) => {
    const t = `${s.geography ?? ""} ${s.title} ${s.summary ?? ""}`.toLowerCase();
    return t.includes("astur");
  }), [studies]);

  // Hospital real data
  const hospitalData = useMemo(() =>
    consumption.filter(r => r.geography.toLowerCase().includes("astur") && r.sector === "Hospitalario" && r.packages != null),
    [consumption]
  );

  const completeHospitalData = useMemo(() => {
    const monthsByYear = new Map<number, Set<number>>();
    hospitalData.forEach((record) => {
      if (!record.month) return;
      if (!monthsByYear.has(record.year)) monthsByYear.set(record.year, new Set());
      monthsByYear.get(record.year)!.add(record.month);
    });
    return hospitalData.filter((record) => (monthsByYear.get(record.year)?.size ?? 0) === 12);
  }, [hospitalData]);

  // ATC derived data for Asturias (DHD, DDD, PVP)
  const asturiasATC = useMemo(() =>
    consumption.filter(r => r.geography === "Asturias" && r.sector === "Recetas SNS ATC"),
    [consumption]
  );

  const asturiasATCDHD = useMemo(() => asturiasATC.filter(r => r.dhd != null), [asturiasATC]);
  const asturiasATCDDD = useMemo(() => asturiasATC.filter(r => r.ddd != null), [asturiasATC]);
  const asturiasATCPVP = useMemo(() => asturiasATC.filter(r => r.amount_pvpiva != null), [asturiasATC]);

  // Year-over-year for hospital packages
  const hospitalYOY = useMemo(() => {
    const byYear = new Map<number, number>();
    completeHospitalData.forEach((r) => { byYear.set(r.year, (byYear.get(r.year) ?? 0) + Number(r.packages ?? 0)); });
    const sorted = [...byYear.entries()].sort((a, b) => a[0] - b[0]);
    const changes: { year: number; total: number; change: number | null }[] = [];
    for (let i = 0; i < sorted.length; i++) {
      const [year, total] = sorted[i];
      const prev = i > 0 ? sorted[i - 1][1] : 0;
      changes.push({ year, total, change: prev > 0 ? Number(((total - prev) / prev * 100).toFixed(1)) : null });
    }
    return changes;
  }, [completeHospitalData]);

  if (loading) return <LoadingState />;

  const totalPackages = hospitalData.reduce((s, r) => s + Number(r.packages ?? 0), 0);
  const monthsCount = new Set(hospitalData.map(r => `${r.year}-${r.month}`)).size;

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Ámbito regional</p>
          <h1>Asturias</h1>
          <p>Datos reales de consumo farmacéutico del SNS para el Principado de Asturias.</p>
        </div>
      </header>

      <MetricStrip
        metrics={[
          { label: "Meses con datos", value: monthsCount, tone: "teal" },
          { label: "Total envases hospital", value: totalPackages.toLocaleString("es-ES"), tone: "ink" },
          { label: "ATC codes", value: new Set(asturiasATCDHD.map(r => r.atc_code).filter(Boolean)).size, tone: "teal" },
          { label: "Documentos", value: asturiasStudies.length, tone: "rust" },
        ]}
      />

      {/* DHD, DDD, PVP for Asturias */}
      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>DHD — Dosis por Habitante y Día (media anual)</h2>
            <p className="muted">Estimado desde datos ATC nacionales con factor regional</p>
          </div>
          {asturiasATCDHD.length ? <TimeSeriesChart records={asturiasATCDHD} metric="dhd" maxSeries={8} /> : <EmptyState message="Sin datos DHD para Asturias." />}
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>DDD — Dosis Diaria Definida (total)</h2>
            <p className="muted">Estimado desde datos nacionales × población</p>
          </div>
          {asturiasATCDDD.length ? <TimeSeriesChart records={asturiasATCDDD} metric="ddd" maxSeries={8} /> : <EmptyState message="Sin datos DDD para Asturias." />}
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>PVP IVA — Importe estimado</h2>
            <p className="muted">Estimado desde datos nacionales con factor regional</p>
          </div>
          {asturiasATCPVP.length ? <TimeSeriesChart records={asturiasATCPVP} metric="amount_pvpiva" maxSeries={8} /> : <EmptyState message="Sin datos PVP IVA para Asturias." />}
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Envases hospitalarios (datos reales SNS)</h2>
            <p className="muted">Total anual en hospitales públicos (años completos)</p>
          </div>
          {completeHospitalData.length ? <TimeSeriesChart records={completeHospitalData} metric="packages" /> : <EmptyState message="Sin datos hospitalarios." />}
        </div>
      </section>

      {/* Annual totals */}
      <section className="panel">
        <div className="panel-heading">
          <h2>Total anual de envases hospitalarios en Asturias</h2>
        </div>
        <table className="data-table full">
          <thead><tr><th>Año</th><th>Total envases</th><th>Variación interanual</th></tr></thead>
          <tbody>
            {hospitalYOY.map(({ year, total, change }) => (
              <tr key={year}>
                <td><strong>{year}</strong></td>
                <td>{total.toLocaleString("es-ES")}</td>
                <td>
                  {change !== null ? (
                    <span className={`badge ${change > 0 ? "badge-rust" : "badge-teal"}`}>
                      {change > 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                      {change > 0 ? "+" : ""}{change}%
                    </span>
                  ) : <span className="muted">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Documents and sources */}
      <section className="grid two">
        <div className="panel">
          <div className="panel-heading"><h2>Documentos y estudios</h2></div>
          <div className="study-list">
            {asturiasStudies.length ? asturiasStudies.slice(0, 6).map((s) => <StudyCard key={s.id} study={s} />) : <EmptyState message="No se encontraron documentos." />}
          </div>
        </div>
        <div className="panel">
          <div className="panel-heading"><h2>Fuentes de datos</h2></div>
          <div className="source-summary">
            {asturiasSources.length ? asturiasSources.slice(0, 5).map((s) => (
              <div key={s.id}><strong>{s.name}</strong><span>{s.source_type}</span></div>
            )) : <p className="muted">No hay fuentes específicas.</p>}
          </div>
          <p className="muted" style={{ fontSize: 11, marginTop: 8 }}>
            Datos hospitalarios: Ministerio de Sanidad (consumo real SNS). DHD/DDD/PVP: estimados desde datos nacionales con factor regional. Revisar con fuentes CCAA antes de uso clínico.
          </p>
        </div>
      </section>
    </div>
  );
}
