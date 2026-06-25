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
  const aggregated = new Map<string, { sum: number; count: number }>();
  records.forEach((r) => {
    const val = r[metric];
    if (val == null || val === 0) return;
    const key = `${r.geography}|${r.year}`;
    const prev = aggregated.get(key) ?? { sum: 0, count: 0 };
    prev.sum += Number(val);
    prev.count += 1;
    aggregated.set(key, prev);
  });

  if (aggregated.size === 0) return <p className="muted">Sin datos para mostrar en el heatmap.</p>;

  const rawData: { geo: string; year: number; val: number }[] = [];
  aggregated.forEach(({ sum, count }, key) => {
    const [geo, yearStr] = key.split("|");
    const year = Number(yearStr);
    if (!geo || isNaN(year) || count === 0) return;
    rawData.push({ geo, year, val: Number((sum / count).toFixed(2)) });
  });

  const isSpain = (g: string) => g.trim().toLowerCase() === "spain";

  const geos = Array.from(new Set(rawData.map((d) => d.geo))).sort((a, b) => {
    if (isSpain(a)) return 1;
    if (isSpain(b)) return -1;
    return a.localeCompare(b);
  });
  const years = Array.from(new Set(rawData.map((d) => d.year))).sort((a, b) => a - b);
  const geoIndex = new Map(geos.map((g, i) => [g, i]));

  // Build single data array, Spain cells get gray itemStyle
  const data: { value: [number, number, number]; itemStyle: object; label: object }[] = [];
  const ccaaVals: number[] = [];

  for (const { geo, year, val } of rawData) {
    const x = years.indexOf(year);
    const y = geoIndex.get(geo)!;
    if (isSpain(geo)) {
      data.push({
        value: [x, y, val],
        itemStyle: { color: "#e8e8e8", borderColor: "#ccc", borderWidth: 1 },
        label: { color: "#555", fontSize: 10 },
      });
    } else {
      data.push({
        value: [x, y, val],
        itemStyle: { borderColor: "#fff", borderWidth: 1 },
        label: { fontSize: 10 },
      });
      ccaaVals.push(val);
    }
  }

  const minVal = ccaaVals.length ? Math.min(...ccaaVals) : 0;
  const maxVal = ccaaVals.length ? Math.max(...ccaaVals) : 100;
  const unit = METRIC_UNITS[metric] || metric;

  const option = {
    tooltip: {
      position: "top",
      formatter: (params: { data: { value: number[] } }) => {
        const [x, y, v] = params.data.value;
        const geo = geos[y];
        const yr = years[x];
        const label = isSpain(geo) ? "España" : geo;
        if (isSpain(geo)) {
          return `<strong>${label}</strong><br/>Año ${yr}<br/>${v.toFixed(2)} ${unit}<br/><small>Escala independiente (nivel nacional)</small>`;
        }
        return `${label}<br/>Año ${yr}<br/><strong>${v.toFixed(2)} ${unit}</strong>`;
      },
    },
    grid: { left: 160, right: 30, top: 50, bottom: 80 },
    xAxis: {
      type: "category", data: years.map(String),
      name: "Año", nameLocation: "middle", nameGap: 35,
    },
    yAxis: {
      type: "category", data: geos.map(g => isSpain(g) ? "España" : g),
      name: "Territorio", nameLocation: "middle", nameGap: 140,
    },
    visualMap: {
      min: minVal, max: maxVal,
      calculable: true, orient: "horizontal",
      left: "center", bottom: 15,
      text: [`Alto (${unit}/hab/día)`, `Bajo (${unit}/hab/día)`],
      inRange: { color: ["#edf7ed", "#a5d6a7", "#66bb6a", "#2f8f83", "#1b5e50"] },
    },
    series: [{
      type: "heatmap",
      data,
      label: {
        show: true, fontSize: 10,
        formatter: (p: { data: { value: number[] } }) => {
          const [, y, v] = p.data.value;
          return isSpain(geos[y]) ? v.toFixed(1) : v.toFixed(1);
        },
      },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" } },
    }],
  };
  return <ReactECharts option={option} notMerge={true} lazyUpdate={true} style={{ height: 500, width: "100%" }} />;
}
