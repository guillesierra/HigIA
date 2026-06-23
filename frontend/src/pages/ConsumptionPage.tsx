import { Download, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { HeatmapChart } from "../charts/HeatmapChart";
import { RankingChart } from "../charts/RankingChart";
import { TrendChart } from "../charts/TrendChangesChart";
import { ConsumptionChart } from "../components/ConsumptionChart";
import { ConsumptionTable } from "../components/ConsumptionTable";
import { FilterPanel } from "../components/FilterPanel";
import { LoadingState } from "../components/Status";
import { api } from "../services/api";
import { formatEntityKey, getMetricLabel } from "../services/labels";
import type { ConsumptionRecord, TrendResult } from "../types/domain";

export function ConsumptionPage() {
  const [records, setRecords] = useState<ConsumptionRecord[]>([]);
  const [year, setYear] = useState("");
  const [geography, setGeography] = useState("");
  const [atc, setAtc] = useState("");
  const [medicine, setMedicine] = useState("");
  const [metric, setMetric] = useState<"dhd" | "ddd" | "packages" | "amount_pvpiva">("dhd");
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
      return true;
    }),
    [records, year, geography, atc, medicine]
  );

  const trends = useMemo(() => {
    const seriesMap = new Map<string, Map<number, number>>();
    filtered.forEach((r) => {
      const key = `${r.geography}|${r.atc_code ?? "desconocido"}`;
      if (!seriesMap.has(key)) seriesMap.set(key, new Map());
      seriesMap.get(key)!.set(r.year, (seriesMap.get(key)!.get(r.year) ?? 0) + (Number(r[metric]) || 0));
    });
    const results: TrendResult[] = [];
    seriesMap.forEach((yearVals, key) => {
      const sorted = [...yearVals.entries()].sort((a, b) => a[0] - b[0]);
      if (sorted.length < 2) return;
      const years = sorted.map(([y]) => y);
      const values = sorted.map(([, v]) => v);
      const n = years.length;
      const xMean = years.reduce((a, b) => a + b, 0) / n;
      const yMean = values.reduce((a, b) => a + b, 0) / n;
      let num = 0; let den = 0;
      for (let i = 0; i < n; i++) { num += (years[i] - xMean) * (values[i] - yMean); den += (years[i] - xMean) ** 2; }
      const slope = den ? num / den : 0;
      const totalChange = values[0] !== 0 ? (values[n - 1] - values[0]) / Math.abs(values[0]) * 100 : 0;
      const yoy: number[] = [];
      for (let i = 1; i < n; i++) if (values[i - 1] !== 0) yoy.push((values[i] - values[i - 1]) / Math.abs(values[i - 1]) * 100);
      const avgYoy = yoy.length ? yoy.reduce((a, b) => a + b, 0) / yoy.length : 0;
      results.push({
        entity_key: key, metric, slope: Number(slope.toFixed(6)),
        mean_value: Number(yMean.toFixed(4)), total_change: Number(totalChange.toFixed(2)),
        avg_yoy_change: Number(avgYoy.toFixed(2)),
        trend_direction: slope > 0.01 ? "increasing" : slope < -0.01 ? "decreasing" : "stable",
        years, values: values.map(v => Number(v.toFixed(4))),
        start_value: values[0] ?? null, end_value: values[n - 1] ?? null,
      });
    });
    return results.sort((a, b) => Math.abs(b.avg_yoy_change) - Math.abs(a.avg_yoy_change)).slice(0, 6);
  }, [filtered, metric]);

  const stats = useMemo(() => {
    const geoSet = new Set(filtered.map((r) => r.geography));
    const atcSet = new Set(filtered.map((r) => r.atc_code).filter(Boolean));
    const totalDHD = filtered.reduce((sum, r) => sum + Number(r.dhd ?? 0), 0);
    return { geos: geoSet.size, atcs: atcSet.size, totalDHD: totalDHD.toFixed(1) };
  }, [filtered]);

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
            Datos de consumo farmacéutico: {filtered.length} registros | {stats.geos} territorios | {stats.atcs} códigos ATC | DHD total acumulado: {stats.totalDHD}
          </p>
        </div>
        <a className="download-link" href={`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`} download="higia-consumo.csv">
          <Download size={16} />
          CSV
        </a>
      </header>

      <FilterPanel>
        <input value={year} onChange={(event) => setYear(event.target.value)} placeholder="Año" inputMode="numeric" />
        <input value={geography} onChange={(event) => setGeography(event.target.value)} placeholder="Comunidad Autónoma" />
        <input value={atc} onChange={(event) => setAtc(event.target.value)} placeholder="Código ATC" />
        <input value={medicine} onChange={(event) => setMedicine(event.target.value)} placeholder="Medicamento" />
        <select value={metric} onChange={(event) => setMetric(event.target.value as "dhd" | "ddd" | "packages" | "amount_pvpiva")}>
          <option value="dhd">DHD (Dosis/Hab/Día)</option>
          <option value="ddd">DDD (Dosis Diaria Definida)</option>
          <option value="packages">Envases</option>
          <option value="amount_pvpiva">PVP IVA (Importe)</option>
        </select>
      </FilterPanel>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Evolución anual del consumo</h2>
            <p className="muted">{metricLabel} — cada línea representa un territorio y grupo ATC</p>
          </div>
          <ConsumptionChart records={filtered} metric={metric} />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Ranking de consumo por DHD</h2>
            <p className="muted">Grupos ATC con mayor DHD acumulada</p>
          </div>
          <RankingChart records={filtered} />
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Mapa de calor: Geografía × Año</h2>
            <p className="muted">Cada celda muestra el valor de {metricLabel} para ese territorio y año</p>
          </div>
          <HeatmapChart records={filtered} metric={metric} />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Tendencias detectadas</h2>
            <p className="muted">Variación interanual del consumo por territorio y grupo ATC</p>
          </div>
          {trends.length ? (
            <div className="trends-list">
              {trends.map((t) => (
                <div key={t.entity_key} className="trend-row">
                  <span className="trend-key" title={formatEntityKey(t.entity_key)}>
                    {formatEntityKey(t.entity_key)}
                  </span>
                  <span className={`badge ${t.trend_direction === "increasing" ? "badge-rust" : t.trend_direction === "decreasing" ? "badge-teal" : "badge-ink"}`}>
                    {t.trend_direction === "increasing" ? <TrendingUp size={11} /> : t.trend_direction === "decreasing" ? <TrendingDown size={11} /> : null}
                    {t.avg_yoy_change}%
                  </span>
                </div>
              ))}
            </div>
          ) : <p className="muted">No se detectaron tendencias significativas con los filtros actuales.</p>}
        </div>
      </section>

      <ConsumptionTable records={filtered} />
    </div>
  );
}

function makeCsv(rows: ConsumptionRecord[]) {
  const header = ["year", "geography", "sector", "atc_code", "category", "drug_name", "active_ingredient", "dhd", "packages"];
  const lines = rows.map((row) =>
    header
      .map((key) => {
        const value = row[key as keyof ConsumptionRecord] ?? "";
        return `"${String(value).replace(/"/g, '""')}"`;
      })
      .join(",")
  );
  return [header.join(","), ...lines].join("\n");
}
