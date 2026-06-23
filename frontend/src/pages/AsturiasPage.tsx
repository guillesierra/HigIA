import { TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { HeatmapChart } from "../charts/HeatmapChart";
import { RankingChart } from "../charts/RankingChart";
import { TimeSeriesChart } from "../charts/TimeSeriesChart";
import { MetricStrip } from "../components/MetricStrip";
import { StudyCard } from "../components/StudyCard";
import { EmptyState, LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { ConsumptionRecord, SafetyAlert, Source, StudyDocument, TrendResult } from "../types/domain";

export function AsturiasPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [studies, setStudies] = useState<StudyDocument[]>([]);
  const [consumption, setConsumption] = useState<ConsumptionRecord[]>([]);
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.sources(), api.studies(), api.consumption(), api.alerts()])
      .then(([s, st, c, a]) => { setSources(s); setStudies(st); setConsumption(c); setAlerts(a); })
      .finally(() => setLoading(false));
  }, []);

  const asturiasSources = useMemo(() => sources.filter((s) => `${s.name} ${s.url}`.toLowerCase().includes("astur")), [sources]);
  const asturiasStudies = useMemo(() => studies.filter((s) => {
    const t = `${s.geography ?? ""} ${s.title} ${s.summary ?? ""} ${s.therapeutic_group ?? ""}`.toLowerCase();
    return t.includes("astur") && t.includes(query.toLowerCase());
  }), [studies, query]);

  const asturiasConsumption = useMemo(() =>
    consumption.filter((r) => r.geography.toLowerCase().includes("astur")),
    [consumption]
  );

  // Hospital data has packages but no DHD - use separately
  const hospitalCons = useMemo(() =>
    asturiasConsumption.filter(r => r.sector === "Hospitalario" && r.packages != null),
    [asturiasConsumption]
  );
  const outpatientDHD = useMemo(() =>
    asturiasConsumption.filter(r => r.sector === "Extrahospitalario" && r.dhd != null),
    [asturiasConsumption]
  );

  const asturiasTrends = useMemo(() => {
    const sm = new Map<string, Map<number, number>>();
    asturiasConsumption.forEach((r) => {
      const dhd = Number(r.dhd ?? 0);
      if (dhd <= 0) return;
      const key = `${r.atc_code ?? "total"} (${r.sector ?? "todos"})`;
      if (!sm.has(key)) sm.set(key, new Map());
      sm.get(key)!.set(r.year, (sm.get(key)!.get(r.year) ?? 0) + dhd);
    });
    const results: TrendResult[] = [];
    sm.forEach((yv, key) => {
      const sorted = [...yv.entries()].sort((a, b) => a[0] - b[0]);
      if (sorted.length < 2) return;
      const years = sorted.map(([y]) => y); const values = sorted.map(([, v]) => v);
      const n = years.length; const xm = years.reduce((a, b) => a + b, 0) / n; const ym = values.reduce((a, b) => a + b, 0) / n;
      let num = 0; let den = 0;
      for (let i = 0; i < n; i++) { num += (years[i] - xm) * (values[i] - ym); den += (years[i] - xm) ** 2; }
      const slope = den ? num / den : 0;
      const totalChange = values[0] !== 0 ? (values[n - 1] - values[0]) / Math.abs(values[0]) * 100 : 0;
      const yoy: number[] = [];
      for (let i = 1; i < n; i++) if (values[i - 1] !== 0) yoy.push((values[i] - values[i - 1]) / Math.abs(values[i - 1]) * 100);
      results.push({
        entity_key: key, metric: "dhd", slope: Number(slope.toFixed(6)),
        mean_value: Number(ym.toFixed(4)), total_change: Number(totalChange.toFixed(2)),
        avg_yoy_change: yoy.length ? Number((yoy.reduce((a, b) => a + b, 0) / yoy.length).toFixed(2)) : 0,
        trend_direction: slope > 0.01 ? "increasing" : slope < -0.01 ? "decreasing" : "stable",
        years, values: values.map(v => Number(v.toFixed(4))),
        start_value: values[0] ?? null, end_value: values[n - 1] ?? null,
      });
    });
    return results.sort((a, b) => Math.abs(b.avg_yoy_change) - Math.abs(a.avg_yoy_change));
  }, [asturiasConsumption]);

  if (loading) return <LoadingState />;

  const totalPackages = asturiasConsumption.reduce((s, r) => s + Number(r.packages ?? 0), 0);

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Ámbito regional</p>
          <h1>Asturias</h1>
          <p>Dashboard de consumo farmacéutico, documentos públicos y tendencias para el Principado de Asturias.</p>
        </div>
      </header>

      <MetricStrip
        metrics={[
          { label: "Registros consumo", value: asturiasConsumption.length, tone: "teal" },
          { label: "Hospitalario", value: hospitalCons.length, tone: "ink" },
          { label: "Extrahospitalario", value: outpatientDHD.length, tone: "teal" },
          { label: "Documentos", value: asturiasStudies.length, tone: "rust" },
          { label: "Total envases", value: totalPackages.toLocaleString("es-ES"), tone: "ink" },
        ]}
      />

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Evolución del consumo en Asturias</h2>
            <p className="muted">DHD por grupo ATC a lo largo del tiempo</p>
          </div>
          <TimeSeriesChart records={asturiasConsumption} metric="dhd" />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Envases consumidos en hospitales</h2>
            <p className="muted">Datos mensuales reales del SNS</p>
          </div>
          <TimeSeriesChart records={hospitalCons} metric="packages" />
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Tendencias de consumo en Asturias</h2>
            <p className="muted">Dirección del cambio por grupo ATC y sector</p>
          </div>
          {asturiasTrends.length ? (
            <div className="trends-list" style={{ maxHeight: 320 }}>
              {asturiasTrends.slice(0, 8).map((t) => (
                <div key={t.entity_key} className="trend-row">
                  <span className="trend-key">{t.entity_key}</span>
                  <span className={`badge ${t.trend_direction === "increasing" ? "badge-rust" : t.trend_direction === "decreasing" ? "badge-teal" : "badge-ink"}`}>
                    {t.trend_direction === "increasing" ? <TrendingUp size={11} /> : t.trend_direction === "decreasing" ? <TrendingDown size={11} /> : null}
                    {t.avg_yoy_change}% anual
                  </span>
                </div>
              ))}
            </div>
          ) : <p className="muted">Sin datos suficientes para calcular tendencias.</p>}
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Ranking de grupos ATC</h2>
            <p className="muted">Mayor DHD acumulado en Asturias</p>
          </div>
          <RankingChart records={asturiasConsumption} />
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Documentos y estudios</h2>
            <p className="muted">Publicaciones relacionadas con Asturias</p>
          </div>
          <div className="study-list">
            {asturiasStudies.length ? asturiasStudies.slice(0, 6).map((s) => <StudyCard key={s.id} study={s} />) : <EmptyState message="No se encontraron documentos para Asturias." />}
          </div>
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Fuentes de datos</h2>
            <p className="muted">Orígenes de información disponibles para Asturias</p>
          </div>
          <div className="source-summary">
            {asturiasSources.length ? asturiasSources.slice(0, 5).map((s) => (
              <div key={s.id}><strong>{s.name}</strong><span>{s.source_type}</span></div>
            )) : <p className="muted">No se encontraron fuentes específicas de Asturias.</p>}
          </div>
          <div className="availability" style={{ marginTop: 12 }}>
            <p className="muted" style={{ fontSize: 12 }}>
              Los datos hospitalarios provienen del Ministerio de Sanidad (consumo en hospitales de la red pública del SNS).
              Los datos extrahospitalarios son patrones representativos basados en informes públicos del PRAN.
            </p>
          </div>
        </div>
      </section>

      {asturiasConsumption.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <h2>Mapa temporal: Asturias por año y grupo ATC</h2>
          </div>
          <HeatmapChart records={asturiasConsumption} />
        </section>
      )}
    </div>
  );
}
