import ReactECharts from "echarts-for-react";
import type { ConsumptionRecord } from "../types/domain";
import { getMetricLabel } from "../services/labels";

type Props = {
  records: ConsumptionRecord[];
  metric?: "dhd" | "ddd" | "packages" | "amount_pvpiva";
};

const METRIC_UNITS: Record<string, string> = {
  dhd: "DHD",
  ddd: "DDD",
  packages: "envases",
  amount_pvpiva: "Euros",
};

export function TimeSeriesChart({ records, metric = "dhd" }: Props) {
  // Filter out records where the selected metric is null/undefined
  const valid = records.filter((r) => r[metric] != null);
  const seriesMap = new Map<string, Map<number, number>>();
  valid.forEach((record) => {
    const atcLabel = record.atc_code || record.drug_name || "Total";
    const name = `${record.geography} | ${atcLabel}`;
    if (!seriesMap.has(name)) seriesMap.set(name, new Map());
    seriesMap.get(name)!.set(record.year, Number(record[metric] ?? 0));
  });
  const years = Array.from(new Set(valid.map((record) => record.year))).sort();
  const unit = METRIC_UNITS[metric] || metric;
  const metricLabel = getMetricLabel(metric);

  const option = {
    tooltip: {
      trigger: "axis",
      formatter: (params: { seriesName: string; data: number; axisValue: string }[]) => {
        if (!params.length) return "";
        const name = params[0]?.seriesName;
        const val = params[0]?.data;
        return `${name}<br/>Año ${params[0]?.axisValue}: <b>${val?.toFixed(2)} ${unit}</b>`;
      },
    },
    legend: { top: 0, type: "scroll", textStyle: { fontSize: 11 } },
    grid: { left: 65, right: 20, top: 56, bottom: 45 },
    xAxis: {
      type: "category",
      data: years,
      name: "Año",
      nameLocation: "middle",
      nameGap: 30,
    },
    yAxis: {
      type: "value",
      name: metricLabel,
      nameLocation: "middle",
      nameGap: 55,
    },
    series: Array.from(seriesMap.entries()).map(([name, values]) => ({
      name,
      type: "line",
      smooth: true,
      symbolSize: 7,
      data: years.map((year) => values.get(year) ?? null),
    })),
  };
  return <ReactECharts option={option} style={{ height: 380, width: "100%" }} />;
}
