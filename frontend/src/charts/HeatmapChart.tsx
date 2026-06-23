import ReactECharts from "echarts-for-react";
import type { ConsumptionRecord } from "../types/domain";

type Props = {
  records: ConsumptionRecord[];
  metric?: "dhd" | "ddd" | "packages" | "amount_pvpiva";
};

const METRIC_UNITS: Record<string, string> = {
  dhd: "DHD",
  ddd: "DDD",
  packages: "Envases",
  amount_pvpiva: "Euros",
};

export function HeatmapChart({ records, metric = "dhd" }: Props) {
  const aggregated = new Map<string, number>();
  records.forEach((r) => {
    const key = `${r.geography}|${r.year}`;
    aggregated.set(key, (aggregated.get(key) ?? 0) + Number(r[metric] ?? 0));
  });

  // Collect raw triples, only non-empty
  const rawData: { geo: string; year: number; val: number }[] = [];
  aggregated.forEach((val, key) => {
    if (val <= 0.001) return;
    const [geo, yearStr] = key.split("|");
    const year = Number(yearStr);
    if (!geo || isNaN(year)) return;
    rawData.push({ geo, year, val: Number(val.toFixed(2)) });
  });

  if (rawData.length === 0) return <p className="muted">Sin datos para mostrar en el heatmap.</p>;

  const geos = Array.from(new Set(rawData.map((d) => d.geo))).sort();
  const years = Array.from(new Set(rawData.map((d) => d.year))).sort((a, b) => a - b);
  const geoIndex = new Map(geos.map((g, i) => [g, i]));

  const mappedData: [number, number, number][] = rawData.map((d) => {
    const x = years.indexOf(d.year);
    const y = geoIndex.get(d.geo)!;
    return [x, y, d.val];
  });

  const allVals = mappedData.map((d) => d[2]);
  const unit = METRIC_UNITS[metric] || metric;

  const option = {
    tooltip: {
      position: "top",
      formatter: (params: { data: number[] }) => {
        const [x, y, v] = params.data;
        const geo = geos[y];
        const year = years[x];
        return `${geo}<br/>Año ${year}<br/><strong>${v.toFixed(2)} ${unit}</strong>`;
      },
    },
    grid: { left: 160, right: 24, top: 60, bottom: 80 },
    xAxis: {
      type: "category",
      data: years.map(String),
      name: "Año",
      nameLocation: "middle",
      nameGap: 35,
    },
    yAxis: {
      type: "category",
      data: geos,
      name: "Comunidad Autónoma",
      nameLocation: "middle",
      nameGap: 140,
    },
    visualMap: {
      min: Math.min(...allVals),
      max: Math.max(...allVals),
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      text: [`Alto (${unit})`, `Bajo (${unit})`],
      inRange: { color: ["#edf7ed", "#a5d6a7", "#66bb6a", "#2f8f83", "#1b5e50"] },
    },
    series: [
      {
        type: "heatmap",
        data: mappedData,
        label: { show: true, fontSize: 10, formatter: (p: { data: number[] }) => p.data[2].toFixed(1) },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" } },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 480, width: "100%" }} />;
}
