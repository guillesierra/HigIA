import ReactECharts from "echarts-for-react";
import type { ConsumptionRecord } from "../types/domain";
import { getMetricLabel } from "../services/labels";

type Props = {
  records: ConsumptionRecord[];
  metric?: "dhd" | "ddd" | "packages" | "amount_pvpiva";
  maxSeries?: number;
};

const METRIC_UNITS: Record<string, string> = {
  dhd: "DHD",
  ddd: "DDD",
  packages: "envases",
  amount_pvpiva: "Euros",
};

type Bucket = { total: number; count: number };

export function TimeSeriesChart({ records, metric = "dhd", maxSeries }: Props) {
  const valid = records.filter((r) => r[metric] != null && Number.isFinite(Number(r[metric])));
  const seriesMap = new Map<string, Map<number, Bucket>>();
  valid.forEach((record) => {
    const name = getCurveName(record);
    const value = Number(record[metric] ?? 0);
    if (!seriesMap.has(name)) seriesMap.set(name, new Map());
    const yearMap = seriesMap.get(name)!;
    const current = yearMap.get(record.year) ?? { total: 0, count: 0 };
    current.total += value;
    current.count += 1;
    yearMap.set(record.year, current);
  });
  const years = Array.from(new Set(valid.map((record) => record.year))).sort((a, b) => a - b);
  const unit = METRIC_UNITS[metric] || metric;
  const metricLabel = getMetricLabel(metric);
  const seriesEntries = Array.from(seriesMap.entries())
    .map(([name, values]) => ({
      name,
      values,
      rankValue: Array.from(values.values()).reduce((total, bucket) => total + getBucketValue(bucket, metric), 0),
    }))
    .sort((a, b) => b.rankValue - a.rankValue || a.name.localeCompare(b.name))
    .slice(0, maxSeries ?? seriesMap.size);

  const option = {
    tooltip: {
      trigger: "axis",
      formatter: (params: { seriesName: string; data: number | null; axisValue: string }[]) => {
        if (!params.length) return "";
        const name = params[0]?.seriesName;
        const val = params[0]?.data;
        const formatted = typeof val === "number" ? val.toFixed(2) : "N/D";
        return `${name}<br/>Año ${params[0]?.axisValue}: <b>${formatted} ${unit}</b>`;
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
    series: seriesEntries.map(({ name, values }) => ({
      name,
      type: "line",
      smooth: false,
      connectNulls: true,
      symbolSize: 5,
      lineStyle: { width: 1.5 },
      data: years.map((year) => {
        const bucket = values.get(year);
        return bucket ? Number(getBucketValue(bucket, metric).toFixed(4)) : null;
      }),
    })),
  };
  return <ReactECharts option={option} notMerge={true} lazyUpdate={true} style={{ height: 380, width: "100%" }} />;
}

function getCurveName(record: ConsumptionRecord) {
  const label = record.atc_code || record.drug_name || record.active_ingredient || record.category || record.sector || "Total";
  return `${record.geography} | ${label}`;
}

function getBucketValue(bucket: Bucket, metric: Props["metric"]) {
  return metric === "dhd" ? bucket.total / bucket.count : bucket.total;
}
