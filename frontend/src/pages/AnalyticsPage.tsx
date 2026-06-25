import { ChevronDown, ChevronUp, TrendingDown, TrendingUp } from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import { HeatmapChart } from "../charts/HeatmapChart";
import { RankingChart } from "../charts/RankingChart";
import { TimeSeriesChart } from "../charts/TimeSeriesChart";
import { TrendChart } from "../charts/TrendChangesChart";
import { MetricStrip } from "../components/MetricStrip";
import { LoadingState } from "../components/Status";
import { api } from "../services/api";
import { formatEntityKey } from "../services/labels";
import type { ConsumptionRecord, CorrelationPair, ExportSummary, TrendResult } from "../types/domain";

const MIN_ANALYTICS_YEARS = 8;

export function AnalyticsPage() {
  const [consumption, setConsumption] = useState<ConsumptionRecord[]>([]);
  const [summary, setSummary] = useState<ExportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedTrend, setExpandedTrend] = useState<string | null>(null);
  const [expandedCorr, setExpandedCorr] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([api.consumption(), api.summary()]).then(([c, s]) => {
      setConsumption(c);
      setSummary(s);
    }).finally(() => setLoading(false));
  }, []);

  const annualAtcRecords = useMemo(() => {
    return consumption.filter((record) => {
      if (record.sector !== "Recetas SNS ATC") return false;
      if (!record.atc_code) return false;
      return record.geography_type === "autonomous_community" || isSpain(record.geography);
    });
  }, [consumption]);

  const communityAnnualAtcRecords = useMemo(() => {
    return annualAtcRecords.filter((record) => record.geography_type === "autonomous_community");
  }, [annualAtcRecords]);

  const trends = useMemo(() => {
    if (!communityAnnualAtcRecords.length) return [] as TrendResult[];
    const sm = new Map<string, Map<number, number>>();
    communityAnnualAtcRecords.forEach((r) => {
      // Group by ATC code + geographic level
      const key = r.atc_code
        ? `${r.geography}|${r.atc_code}`
        : `${r.geography}|total`;
      if (!sm.has(key)) sm.set(key, new Map());
      const dhd = Number(r.dhd ?? 0);
      if (dhd > 0) sm.get(key)!.set(r.year, (sm.get(key)!.get(r.year) ?? 0) + dhd);
    });
    const results: TrendResult[] = [];
    sm.forEach((yv, key) => {
      const sorted = [...yv.entries()].sort((a, b) => a[0] - b[0]);
      if (sorted.length < MIN_ANALYTICS_YEARS) return;
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
        trend_direction: slope > 0.005 ? "increasing" : slope < -0.005 ? "decreasing" : "stable",
        years, values: values.map(v => Number(v.toFixed(4))),
        start_value: values[0] ?? null, end_value: values[n - 1] ?? null,
      });
    });
    return results.sort((a, b) => Math.abs(b.avg_yoy_change) - Math.abs(a.avg_yoy_change));
  }, [communityAnnualAtcRecords]);

  const correlations = useMemo(() => api.correlationsCompute(communityAnnualAtcRecords), [communityAnnualAtcRecords]);

  const increasingTrends = trends.filter(t => t.trend_direction === "increasing");
  const decreasingTrends = trends.filter(t => t.trend_direction === "decreasing");
  const strongPosCorr = correlations.filter(c => c.correlation > 0.7);
  const strongNegCorr = correlations.filter(c => c.correlation < -0.7);

  if (loading) return <LoadingState />;

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Análisis de datos</p>
          <h1>Análisis Avanzado</h1>
          <p>Tendencias de consumo, correlaciones entre territorios y grupos ATC, y patrones geográficos.</p>
        </div>
      </header>

      <MetricStrip
        metrics={[
          { label: "Al alza", value: increasingTrends.length, tone: "rust" },
          { label: "A la baja", value: decreasingTrends.length, tone: "teal" },
          { label: "Corr. + fuertes (r>0,7)", value: strongPosCorr.length, tone: "teal" },
          { label: "Corr. − fuertes (r<−0,7)", value: strongNegCorr.length, tone: "rust" },
        ]}
      />

      {/* TENDENCIAS - gráfico principal */}
      <section className="panel">
        <div className="panel-heading">
          <h2>Tendencias de consumo por territorio y grupo ATC</h2>
          <p className="muted">Cada línea = evolución temporal de DHD para un par (territorio, grupo ATC). Pendiente positiva = consumo creciente.</p>
        </div>
        <TrendChart trends={trends} limit={8} title="Series con mayor cambio interanual" />
      </section>

      {/* TENDENCIAS - tablas expandibles */}
      <section className="grid two">
        {/* Al alza */}
        <div className="panel">
          <div className="panel-heading">
            <h2><TrendingUp size={16} style={{ verticalAlign: "middle" }} /> Tendencias al alza ({increasingTrends.length})</h2>
          </div>
          <div style={{ maxHeight: 500, overflow: "auto" }}>
            <table className="data-table full">
              <thead><tr><th>Territorio &gt; Grupo ATC</th><th>Variación anual</th><th>Inicio</th><th>Fin</th><th></th></tr></thead>
              <tbody>
                {increasingTrends.slice(0, 20).map((t) => (
                  <React.Fragment key={t.entity_key}>
                    <tr className="clickable" onClick={() => setExpandedTrend(expandedTrend === t.entity_key ? null : t.entity_key)} style={{ cursor: "pointer" }}>
                      <td title={formatEntityKey(t.entity_key)}>{formatEntityKey(t.entity_key)}</td>
                      <td><span className="badge badge-rust"><TrendingUp size={10} /> +{t.avg_yoy_change}%/año</span></td>
                      <td>{t.start_value?.toFixed(2)}</td>
                      <td>{t.end_value?.toFixed(2)}</td>
                      <td>{expandedTrend === t.entity_key ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</td>
                    </tr>
                    {expandedTrend === t.entity_key && (
                      <tr key={`${t.entity_key}-detail`}>
                        <td colSpan={5} style={{ padding: "12px 16px", background: "#f8f7f4" }}>
                          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                            <strong>{formatEntityKey(t.entity_key)}</strong>
                            <div className="grid four" style={{ marginTop: 4 }}>
                              <div className="mini-card"><span className="mini-value" style={{ fontSize: 18 }}>{t.start_value?.toFixed(2)}</span><span className="mini-label">Valor inicial (DHD)</span></div>
                              <div className="mini-card"><span className="mini-value" style={{ fontSize: 18 }}>{t.end_value?.toFixed(2)}</span><span className="mini-label">Valor final (DHD)</span></div>
                              <div className="mini-card"><span className="mini-value" style={{ fontSize: 18, color: "#b45f3b" }}>{t.total_change}%</span><span className="mini-label">Cambio total</span></div>
                              <div className="mini-card"><span className="mini-value" style={{ fontSize: 18, color: "#b45f3b" }}>+{t.avg_yoy_change}%</span><span className="mini-label">Variación media anual</span></div>
                            </div>
                            <p className="muted" style={{ fontSize: 12 }}>Años analizados: {t.years.join(", ")} | Media: {t.mean_value.toFixed(2)} DHD | Pendiente: {t.slope}</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* A la baja */}
        <div className="panel">
          <div className="panel-heading">
            <h2><TrendingDown size={16} style={{ verticalAlign: "middle" }} /> Tendencias a la baja ({decreasingTrends.length})</h2>
          </div>
          <div style={{ maxHeight: 500, overflow: "auto" }}>
            <table className="data-table full">
              <thead><tr><th>Territorio &gt; Grupo ATC</th><th>Variación anual</th><th>Inicio</th><th>Fin</th><th></th></tr></thead>
              <tbody>
                {decreasingTrends.slice(0, 20).map((t) => (
                  <React.Fragment key={t.entity_key}>
                    <tr className="clickable" onClick={() => setExpandedTrend(expandedTrend === t.entity_key ? null : t.entity_key)} style={{ cursor: "pointer" }}>
                      <td title={formatEntityKey(t.entity_key)}>{formatEntityKey(t.entity_key)}</td>
                      <td><span className="badge badge-teal"><TrendingDown size={10} /> {t.avg_yoy_change}%/año</span></td>
                      <td>{t.start_value?.toFixed(2)}</td>
                      <td>{t.end_value?.toFixed(2)}</td>
                      <td>{expandedTrend === t.entity_key ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</td>
                    </tr>
                    {expandedTrend === t.entity_key && (
                      <tr key={`${t.entity_key}-detail`}>
                        <td colSpan={5} style={{ padding: "12px 16px", background: "#f8f7f4" }}>
                          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                            <strong>{formatEntityKey(t.entity_key)}</strong>
                            <div className="grid four" style={{ marginTop: 4 }}>
                              <div className="mini-card"><span className="mini-value" style={{ fontSize: 18 }}>{t.start_value?.toFixed(2)}</span><span className="mini-label">Valor inicial (DHD)</span></div>
                              <div className="mini-card"><span className="mini-value" style={{ fontSize: 18 }}>{t.end_value?.toFixed(2)}</span><span className="mini-label">Valor final (DHD)</span></div>
                              <div className="mini-card"><span className="mini-value" style={{ fontSize: 18, color: "#2f8f83" }}>{t.total_change}%</span><span className="mini-label">Cambio total</span></div>
                              <div className="mini-card"><span className="mini-value" style={{ fontSize: 18, color: "#2f8f83" }}>{t.avg_yoy_change}%</span><span className="mini-label">Variación media anual</span></div>
                            </div>
                            <p className="muted" style={{ fontSize: 12 }}>Años analizados: {t.years.join(", ")} | Media: {t.mean_value.toFixed(2)} DHD | Pendiente: {t.slope}</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CORRELACIONES */}
      <section className="panel">
        <div className="panel-heading">
          <h2>Correlaciones entre territorios y grupos ATC</h2>
          <p className="muted">
            Coeficiente de Pearson (r) entre pares de series (territorio, ATC). r cercano a +1 = evolucionan en la misma dirección.
            r cercano a −1 = cuando una sube, la otra baja. r cercano a 0 = sin relación. Se muestran solo correlaciones con r ≠ 0.
          </p>
        </div>
        <div style={{ maxHeight: 500, overflow: "auto" }}>
          <table className="data-table full">
            <thead>
              <tr><th>Serie A</th><th>Serie B</th><th>r</th><th>Interpretación</th><th>Años</th><th></th></tr>
            </thead>
            <tbody>
              {correlations.slice(0, 30).map((c, i) => (
                <React.Fragment key={`corr-${i}`}>
                  <tr className="clickable" onClick={() => setExpandedCorr(expandedCorr === i ? null : i)} style={{ cursor: "pointer" }}>
                    <td title={c.entity_a}>{formatEntityKey(c.entity_a)}</td>
                    <td title={c.entity_b}>{formatEntityKey(c.entity_b)}</td>
                    <td><span className={`badge ${c.correlation > 0.5 ? "badge-teal" : c.correlation < -0.5 ? "badge-rust" : "badge-ink"}`}>{c.correlation}</span></td>
                    <td style={{ fontSize: 12 }}>
                      {c.correlation > 0.7 ? "Positiva fuerte ↑↑" : c.correlation > 0.4 ? "Positiva moderada ↑" : c.correlation > 0 ? "Positiva débil ↗" :
                       c.correlation < -0.7 ? "Negativa fuerte ↓↓" : c.correlation < -0.4 ? "Negativa moderada ↓" : "Negativa débil ↘"}
                    </td>
                    <td>{c.common_years}</td>
                    <td>{expandedCorr === i ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</td>
                  </tr>
                  {expandedCorr === i && (
                    <tr key={`corr-${i}-detail`}>
                      <td colSpan={6} style={{ padding: "12px 16px", background: "#f8f7f4" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <strong>{formatEntityKey(c.entity_a)} ↔ {formatEntityKey(c.entity_b)}</strong>
                          <div className="grid four" style={{ marginTop: 4 }}>
                            <div className="mini-card"><span className="mini-value" style={{ fontSize: 18, color: c.correlation > 0 ? "#2f8f83" : "#b45f3b" }}>{c.correlation}</span><span className="mini-label">Pearson r</span></div>
                            <div className="mini-card"><span className="mini-value" style={{ fontSize: 18 }}>{c.common_years}</span><span className="mini-label">Años en común</span></div>
                            <div className="mini-card"><span className="mini-value" style={{ fontSize: 18 }}>{(c.correlation ** 2 * 100).toFixed(1)}%</span><span className="mini-label">R² (varianza explicada)</span></div>
                            <div className="mini-card"><span className="mini-value" style={{ fontSize: 14 }}>
                              {c.correlation > 0.7 ? "Fuerte directa" : c.correlation > 0.4 ? "Moderada directa" : c.correlation > 0 ? "Débil directa" :
                               c.correlation < -0.7 ? "Fuerte inversa" : c.correlation < -0.4 ? "Moderada inversa" : "Débil inversa"}
                            </span><span className="mini-label">Interpretación</span></div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* HEATMAP */}
      <section className="panel">
        <div className="panel-heading">
          <h2>Mapa de calor: DHD por CCAA y año</h2>
          <p className="muted">Cada celda coloreada corresponde a una comunidad autónoma. España se muestra en gris como referencia fuera de escala.</p>
        </div>
        <HeatmapChart records={annualAtcRecords} />
      </section>

      {/* ESTADÍSTICAS GLOBALES */}
      {summary && (
        <section className="panel" style={{ marginTop: 16 }}>
          <div className="panel-heading"><h2>Estadísticas globales</h2></div>
          <div className="grid four">
            <div className="mini-card"><span className="mini-value">{summary.counts.consumption_records}</span><span className="mini-label">Registros de consumo</span></div>
            <div className="mini-card"><span className="mini-value">{summary.counts.alerts}</span><span className="mini-label">Alertas de seguridad</span></div>
            <div className="mini-card"><span className="mini-value">{summary.counts.atc_codes}</span><span className="mini-label">Códigos ATC</span></div>
            <div className="mini-card"><span className="mini-value">{summary.counts.drugs}</span><span className="mini-label">Medicamentos</span></div>
          </div>
          {summary.year_range && <p className="muted" style={{ marginTop: 8 }}>Periodo de datos: {summary.year_range.min} – {summary.year_range.max}</p>}
        </section>
      )}
    </div>
  );
}

function isSpain(geography: string) {
  const normalized = geography.trim().toLowerCase();
  return normalized === "spain" || normalized === "españa";
}
