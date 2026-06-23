import { Activity, AlertTriangle, BarChart3, Database, GitBranch, MapPinned, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AlertsByYearChart } from "../charts/AlertsByYearChart";
import { HeatmapChart } from "../charts/HeatmapChart";
import { RankingChart } from "../charts/RankingChart";
import { MetricStrip } from "../components/MetricStrip";
import { LoadingState } from "../components/Status";
import { api } from "../services/api";
import { formatEntityKey } from "../services/labels";
import type { ConsumptionRecord, ExportSummary, SafetyAlert, Source, StudyDocument, TrendResult } from "../types/domain";

type HomePageProps = { onNavigate?: (route: string) => void };

export function HomePage({ onNavigate }: HomePageProps) {
  const [sources, setSources] = useState<Source[]>([]);
  const [alerts, setAlerts] = useState<SafetyAlert[]>([]);
  const [consumption, setConsumption] = useState<ConsumptionRecord[]>([]);
  const [studies, setStudies] = useState<StudyDocument[]>([]);
  const [summary, setSummary] = useState<ExportSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.sources(), api.alerts(), api.consumption(), api.studies(), api.summary()])
      .then(([s, a, c, st, sm]) => {
        setSources(s); setAlerts(a); setConsumption(c); setStudies(st); setSummary(sm);
      })
      .finally(() => setLoading(false));
  }, []);

  const trends = useMemo(() => {
    const sm = new Map<string, Map<number, number>>();
    consumption.forEach((r) => {
      const key = `${r.geography}|${r.atc_code ?? "desconocido"}`;
      if (!sm.has(key)) sm.set(key, new Map());
      sm.get(key)!.set(r.year, (sm.get(key)!.get(r.year) ?? 0) + (Number(r.dhd) || 0));
    });
    const results: TrendResult[] = [];
    sm.forEach((yv, key) => {
      const sorted = [...yv.entries()].sort((a, b) => a[0] - b[0]);
      if (sorted.length < 2) return;
      const years = sorted.map(([y]) => y);
      const values = sorted.map(([, v]) => v);
      const n = years.length;
      const xm = years.reduce((a, b) => a + b, 0) / n;
      const ym = values.reduce((a, b) => a + b, 0) / n;
      let num = 0; let den = 0;
      for (let i = 0; i < n; i++) { num += (years[i] - xm) * (values[i] - ym); den += (years[i] - xm) ** 2; }
      const slope = den ? num / den : 0;
      const yoy: number[] = [];
      for (let i = 1; i < n; i++) if (values[i - 1] !== 0) yoy.push((values[i] - values[i - 1]) / Math.abs(values[i - 1]) * 100);
      results.push({
        entity_key: key, metric: "dhd", slope: Number(slope.toFixed(6)),
        mean_value: Number(ym.toFixed(4)), total_change: 0,
        avg_yoy_change: yoy.length ? Number((yoy.reduce((a, b) => a + b, 0) / yoy.length).toFixed(2)) : 0,
        trend_direction: slope > 0.01 ? "increasing" : slope < -0.01 ? "decreasing" : "stable",
        years, values: values.map(v => Number(v.toFixed(4))),
        start_value: values[0] ?? null, end_value: values[n - 1] ?? null,
      });
    });
    return results;
  }, [consumption]);

  if (loading) return <LoadingState />;

  const officialSources = sources.filter((s) => s.source_type.includes("official")).length;
  const geographies = new Set(consumption.map((r) => r.geography)).size;
  const atcCodes = new Set(consumption.map((r) => r.atc_code).filter(Boolean)).size;
  const increasing = trends.filter((t) => t.trend_direction === "increasing").length;
  const decreasing = trends.filter((t) => t.trend_direction === "decreasing").length;
  const yearsSet = new Set(consumption.map((r) => r.year));
  const yearSpan = yearsSet.size ? `${Math.min(...yearsSet)} – ${Math.max(...yearsSet)}` : "N/D";

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Explorador de datos públicos farmacéuticos</p>
          <h1>HigIA</h1>
          <p>
            Plataforma web para explorar información pública sobre medicamentos, alertas sanitarias, consumo agregado,
            códigos ATC, tendencias de uso, correlaciones y documentación relacionada con España.
          </p>
        </div>
      </header>

      <MetricStrip
        metrics={[
          { label: "Fuentes de datos", value: sources.length, tone: "teal" },
          { label: "Fuentes oficiales", value: officialSources, tone: "ink" },
          { label: "Alertas", value: alerts.length, tone: "rust" },
          { label: "Territorios", value: geographies, tone: "teal" },
          { label: "Códigos ATC", value: atcCodes, tone: "ink" },
          { label: "Periodo", value: yearSpan, tone: "ink" },
        ]}
      />

      <section className="section-links" aria-label="Secciones">
        {[
          ["Fuentes", "sources", <Database size={18} />],
          ["Alertas", "alerts", <AlertTriangle size={18} />],
          ["Consumo", "consumption", <Activity size={18} />],
          ["Relaciones", "relations", <GitBranch size={18} />],
          ["Análisis", "analytics", <BarChart3 size={18} />],
          ["Asturias", "asturias", <MapPinned size={18} />],
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
            <h2>Alertas de seguridad por año</h2>
            <p className="muted">Notas de farmacovigilancia emitidas por la AEMPS</p>
          </div>
          <AlertsByYearChart alerts={alerts} />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Ranking de consumo por DHD</h2>
            <p className="muted">Grupos ATC con mayor Dosis por Habitante y Día</p>
          </div>
          <RankingChart records={consumption} />
        </div>
      </section>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Mapa de calor: Geografía × Año (DHD)</h2>
            <p className="muted">Consumo de medicamentos por territorio y año</p>
          </div>
          <HeatmapChart records={consumption} />
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Tendencias de consumo</h2>
            <p className="muted">Dirección del cambio en el consumo de medicamentos</p>
          </div>
          <div className="grid two-compact" style={{ padding: 12 }}>
            <div className="mini-card">
              <span className="mini-value" style={{ color: "#b45f3b" }}><TrendingUp size={16} /> {increasing}</span>
              <span className="mini-label">Series al alza</span>
            </div>
            <div className="mini-card">
              <span className="mini-value" style={{ color: "#2f8f83" }}><TrendingDown size={16} /> {decreasing}</span>
              <span className="mini-label">Series a la baja</span>
            </div>
            <div className="mini-card">
              <span className="mini-value">{trends.length}</span>
              <span className="mini-label">Series analizadas</span>
            </div>
            <div className="mini-card">
              <span className="mini-value">{trends.filter(t => t.trend_direction === "stable").length}</span>
              <span className="mini-label">Estables</span>
            </div>
          </div>
          {trends.filter(t => t.trend_direction !== "stable").slice(0, 5).map((t) => (
            <div key={t.entity_key} className="trend-row">
              <span className="trend-key" title={formatEntityKey(t.entity_key)}>
                {formatEntityKey(t.entity_key)}
              </span>
              <span className={`badge ${t.trend_direction === "increasing" ? "badge-rust" : "badge-teal"}`}>
                {t.avg_yoy_change}%
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading"><h2>Resumen de fuentes de datos</h2></div>
        <div className="source-summary">
          {sources.slice(0, 6).map((source) => (
            <div key={source.id}>
              <strong>{source.name}</strong>
              <span>{source.source_type}</span>
            </div>
          ))}
        </div>
      </section>

      {summary && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="panel-heading"><h2>Totales de la base de datos</h2></div>
          <div className="grid four">
            <div className="mini-card"><span className="mini-value">{summary.counts.consumption_records}</span><span className="mini-label">Registros de consumo</span></div>
            <div className="mini-card"><span className="mini-value">{summary.counts.studies}</span><span className="mini-label">Documentos</span></div>
            <div className="mini-card"><span className="mini-value">{summary.counts.drugs}</span><span className="mini-label">Medicamentos</span></div>
            <div className="mini-card"><span className="mini-value">{summary.counts.atc_codes}</span><span className="mini-label">Códigos ATC</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
