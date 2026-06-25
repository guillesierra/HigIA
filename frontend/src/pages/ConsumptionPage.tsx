import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ConsumptionChart } from "../components/ConsumptionChart";
import { FilterPanel } from "../components/FilterPanel";
import { LoadingState } from "../components/Status";
import { api } from "../services/api";
import { getAtcName, getMetricLabel } from "../services/labels";
import type { ConsumptionRecord } from "../types/domain";

const PAGE_SIZE = 25;
const DEFAULT_CURVE_LIMIT = 8;

export function ConsumptionPage() {
  const [records, setRecords] = useState<ConsumptionRecord[]>([]);
  const [year, setYear] = useState("");
  const [geography, setGeography] = useState("");
  const [atc, setAtc] = useState("");
  const [medicine, setMedicine] = useState("");
  const [metric, setMetric] = useState<"dhd" | "ddd" | "packages" | "amount_pvpiva">("dhd");
  const [selectedCurves, setSelectedCurves] = useState<Set<string>>(new Set());
  const [curveSearch, setCurveSearch] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.consumption().then(setRecords).finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() =>
    records.filter((record) => {
      const rowText = `${record.atc_code ?? ""} ${record.category ?? ""} ${record.drug_name ?? ""} ${record.active_ingredient ?? ""}`.toLowerCase();
      if (year && record.year !== Number(year)) return false;
      if (geography && !record.geography.toLowerCase().includes(geography.toLowerCase())) return false;
      if (atc && !(record.atc_code ?? record.category ?? "").toLowerCase().startsWith(atc.toLowerCase())) return false;
      if (medicine && !rowText.includes(medicine.toLowerCase())) return false;
      const val = record[metric];
      if (val == null || Number(val) <= 0) return false;
      return true;
    }),
    [records, year, geography, atc, medicine, metric]
  );

  const curveStats = useMemo(() => {
    const stats = new Map<string, number>();
    filtered.forEach((r) => {
      const name = getCurveName(r);
      stats.set(name, (stats.get(name) ?? 0) + Number(r[metric] ?? 0));
    });
    return Array.from(stats.entries()).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }, [filtered, metric]);

  const curveNames = useMemo(() => curveStats.map(([name]) => name).sort(), [curveStats]);

  // Extract unique CCAA from curve names
  const ccaaNames = useMemo(() => {
    const names = new Set<string>();
    curveNames.forEach((n) => { const geo = n.split(" | ")[0]; if (geo) names.add(geo); });
    return Array.from(names).sort();
  }, [curveNames]);

  const selectByCCAA = (ccaa: string) => {
    const next = new Set(selectedCurves);
    curveNames.forEach((n) => { if (n.startsWith(ccaa + " | ")) next.add(n); });
    setSelectedCurves(next);
  };

  const defaultCurves = useMemo(() => curveStats.slice(0, DEFAULT_CURVE_LIMIT).map(([name]) => name), [curveStats]);

  useEffect(() => {
    setSelectedCurves(new Set(defaultCurves));
    setPage(0);
  }, [defaultCurves]);

  const displayRecords = useMemo(() => {
    if (selectedCurves.size === curveNames.length) return filtered;
    return filtered.filter((r) => {
      return selectedCurves.has(getCurveName(r));
    });
  }, [filtered, selectedCurves, curveNames]);

  const visibleCurveNames = useMemo(() => {
    return curveNames
      .filter((name) => !curveSearch || name.toLowerCase().includes(curveSearch.toLowerCase()))
      .sort((a, b) => {
        const selectedDelta = Number(selectedCurves.has(b)) - Number(selectedCurves.has(a));
        return selectedDelta || a.localeCompare(b);
      });
  }, [curveNames, curveSearch, selectedCurves]);

  const stats = useMemo(() => {
    const geoSet = new Set(filtered.map((r) => r.geography));
    const atcSet = new Set(filtered.map((r) => r.atc_code).filter(Boolean));
    return { geos: geoSet.size, atcs: atcSet.size };
  }, [filtered]);

  const totalPages = Math.ceil(displayRecords.length / PAGE_SIZE);
  const pageRecords = displayRecords.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  if (loading) return <LoadingState />;

  const csv = makeCsv(filtered);
  const metricLabel = getMetricLabel(metric);

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Datos agregados de consumo</p>
          <h1>Consumo de medicamentos</h1>
          <p className="muted">
            {filtered.length} registros | {stats.geos} territorios | {stats.atcs} códigos ATC
          </p>
        </div>
        <a className="download-link" href={`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`} download="higia-consumo.csv">
          <Download size={16} /> CSV
        </a>
      </header>

      <FilterPanel>
        <input value={year} onChange={(e) => setYear(e.target.value)} placeholder="Año" inputMode="numeric" />
        <input value={geography} onChange={(e) => setGeography(e.target.value)} placeholder="Comunidad Autónoma" />
        <input value={atc} onChange={(e) => setAtc(e.target.value)} placeholder="Código ATC" />
        <input value={medicine} onChange={(e) => setMedicine(e.target.value)} placeholder="Medicamento" />
        <select value={metric} onChange={(e) => setMetric(e.target.value as typeof metric)}>
          <option value="dhd">DHD (Dosis/Hab/Día)</option>
          <option value="ddd">DDD (Dosis Diaria Definida)</option>
          <option value="packages">Envases</option>
          <option value="amount_pvpiva">PVP IVA (Importe)</option>
        </select>
      </FilterPanel>

      {/* WIDE CHART + LEGEND SELECTOR */}
      <section className="consumption-chart-row">
        <div className="panel chart-wide">
          <div className="panel-heading">
            <h2>Evolución anual — {metricLabel}</h2>
          </div>
          <ConsumptionChart records={displayRecords} metric={metric} />
        </div>
        <div className="panel legend-panel">
          <div className="panel-heading">
            <h2>Curvas</h2>
            <button className="text-button" onClick={() => setSelectedCurves(new Set(defaultCurves))}>Top {DEFAULT_CURVE_LIMIT}</button>
            <button className="text-button" onClick={() => setSelectedCurves(new Set(curveNames))}>Todas</button>
            <button className="text-button" onClick={() => setSelectedCurves(new Set())}>Ninguna</button>
          </div>
          <p className="muted curve-count">{selectedCurves.size} de {curveNames.length}</p>
          <select
            className="curve-search"
            value=""
            onChange={(e) => { if (e.target.value) selectByCCAA(e.target.value); e.target.value = ""; }}
            style={{ marginBottom: 4, fontSize: 11 }}
          >
            <option value="">+ Filtrar por CCAA…</option>
            {ccaaNames.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <input
            className="curve-search"
            type="text"
            placeholder="Buscar curva…"
            value={curveSearch}
            onChange={(e) => setCurveSearch(e.target.value)}
          />
          <div className="curve-list">
            {visibleCurveNames.map((name) => (
                <label key={name} className="curve-item">
                <input type="checkbox" checked={selectedCurves.has(name)} onChange={() => {
                  const next = new Set(selectedCurves);
                  next.has(name) ? next.delete(name) : next.add(name);
                  setSelectedCurves(next);
                }} />
                <span title={name}>{name.length > 35 ? name.slice(0, 35) + "…" : name}</span>
              </label>
            ))}
          </div>
        </div>
      </section>

      {/* PAGINATED TABLE */}
      <section className="panel">
        <div className="panel-heading">
          <h2>Datos ({displayRecords.length} registros)</h2>
          <div className="pagination">
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)}><ChevronLeft size={16} /></button>
            <span>Pág {page + 1} / {totalPages || 1}</span>
            <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}><ChevronRight size={16} /></button>
          </div>
        </div>
        <div style={{ overflow: "auto" }}>
          <table className="data-table full">
            <thead>
              <tr>
                <th>Año</th><th>Mes</th><th>CCAA</th><th>Sector</th>
                <th>ATC</th><th>Medicamento</th>
                <th>DHD</th><th>DDD</th><th>Envases</th><th>PVP IVA</th>
              </tr>
            </thead>
            <tbody>
              {pageRecords.map((r, i) => (
                <tr key={`${r.id || i}`}>
                  <td>{r.year}</td>
                  <td>{r.month ?? "—"}</td>
                  <td>{r.geography}</td>
                  <td>{r.sector ?? "—"}</td>
                  <td>{r.atc_code ? `${getAtcName(r.atc_code)} (${r.atc_code})` : "—"}</td>
                  <td>{r.drug_name ?? r.active_ingredient ?? "—"}</td>
                  <td>{r.dhd != null ? Number(r.dhd).toFixed(2) : "—"}</td>
                  <td>{r.ddd != null ? Number(r.ddd).toLocaleString("es-ES", { maximumFractionDigits: 0 }) : "—"}</td>
                  <td>{r.packages != null ? Number(r.packages).toLocaleString("es-ES", { maximumFractionDigits: 0 }) : "—"}</td>
                  <td>{r.amount_pvpiva != null ? `${Number(r.amount_pvpiva).toLocaleString("es-ES", { maximumFractionDigits: 0 })} €` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function makeCsv(rows: ConsumptionRecord[]) {
  const h = ["year","geography","sector","atc_code","drug_name","dhd","ddd","packages","amount_pvpiva"];
  return [h.join(","), ...rows.map(r => h.map(k => `"${String(r[k as keyof ConsumptionRecord] ?? "").replace(/"/g,'""')}"`).join(","))].join("\n");
}

function getCurveName(record: ConsumptionRecord) {
  const label = record.atc_code || record.drug_name || record.active_ingredient || record.category || record.sector || "Total";
  return `${record.geography} | ${label}`;
}
