import ReactECharts from "echarts-for-react";
import type { TrendResult } from "../types/domain";
import { formatEntityKey, getMetricLabel } from "../services/labels";

type Props = {
  trends: TrendResult[];
  limit?: number;
  title?: string;
};

export function TrendChart({ trends, limit = 10, title }: Props) {
  const top = trends
    .filter((t) => t.trend_direction !== "stable")
    .slice(0, limit);

  if (!top.length) return <p className="muted">No se detectaron tendencias significativas.</p>;

  const metricLabel = getMetricLabel(top[0]?.metric || "dhd");

  const option = {
    title: title ? { text: title, left: "center", textStyle: { fontSize: 13, color: "#42505a" } } : undefined,
    tooltip: {
      trigger: "axis",
      formatter: (params: { seriesName: string; data: number[]; axisValue: string }[]) => {
        if (!params.length) return "";
        const name = params[0]?.seriesName || "";
        const t = top.find((tr) => formatEntityKey(tr.entity_key) === name);
        if (!t) return name;
        return `<strong>${formatEntityKey(t.entity_key)}</strong><br/>
          Tendencia: <b>${t.trend_direction === "increasing" ? "AL ALZA" : "A LA BAJA"}</b><br/>
          Variación media anual: ${t.avg_yoy_change}%<br/>
          Cambio total: ${t.total_change}%<br/>
          Valor inicial: ${t.start_value?.toFixed(2)} DHD → final: ${t.end_value?.toFixed(2)} DHD<br/>
          Media: ${t.mean_value.toFixed(2)} DHD (media por año)`;
      },
    },
    legend: { top: title ? 30 : 0, type: "scroll", textStyle: { fontSize: 11 } },
    grid: { left: 60, right: 24, top: title ? 80 : 50, bottom: 45 },
    xAxis: {
      type: "category",
      data: Array.from(new Set(top.flatMap((t) => t.years))).sort().map(String),
      name: "Año",
      nameLocation: "middle",
      nameGap: 30,
    },
    yAxis: {
      type: "value",
      name: metricLabel,
      nameLocation: "middle",
      nameGap: 45,
    },
    series: top.map((t) => {
      const dir = t.trend_direction === "increasing" ? "↑" : "↓";
      return {
        name: `${formatEntityKey(t.entity_key)} ${dir}${t.avg_yoy_change}%`,
        type: "line",
        smooth: true,
        data: t.years.map((y) => t.values[t.years.indexOf(y)] ?? null),
        symbolSize: 5,
      };
    }),
  };
  return <ReactECharts option={option} style={{ height: 400, width: "100%" }} />;
}
