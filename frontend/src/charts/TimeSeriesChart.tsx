import ReactECharts from "echarts-for-react";
import type { ConsumptionRecord } from "../types/domain";

type Props = {
  records: ConsumptionRecord[];
  metric?: "dhd" | "packages" | "amount_pvpiva";
};

export function TimeSeriesChart({ records, metric = "dhd" }: Props) {
  const seriesMap = new Map<string, Map<number, number>>();
  records.forEach((record) => {
    const name = `${record.geography}${record.atc_code ? ` | ${record.atc_code}` : ""}`;
    if (!seriesMap.has(name)) seriesMap.set(name, new Map());
    const value = Number(record[metric] ?? 0);
    seriesMap.get(name)!.set(record.year, value);
  });
  const years = Array.from(new Set(records.map((record) => record.year))).sort();
  const option = {
    tooltip: { trigger: "axis" },
    legend: { top: 0, type: "scroll" },
    grid: { left: 48, right: 16, top: 56, bottom: 40 },
    xAxis: { type: "category", data: years },
    yAxis: { type: "value", name: metric.toUpperCase() },
    series: Array.from(seriesMap.entries()).map(([name, values]) => ({
      name,
      type: "line",
      smooth: true,
      symbolSize: 7,
      data: years.map((year) => values.get(year) ?? null)
    }))
  };
  return <ReactECharts option={option} style={{ height: 360, width: "100%" }} />;
}

