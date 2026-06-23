import ReactECharts from "echarts-for-react";
import type { ConsumptionRecord } from "../types/domain";

export function RankingChart({ records }: { records: ConsumptionRecord[] }) {
  const totals = new Map<string, number>();
  records.forEach((record) => {
    const label = record.drug_name || record.atc_code || "Unknown";
    totals.set(label, (totals.get(label) ?? 0) + Number(record.dhd ?? 0));
  });
  const entries = Array.from(totals.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .reverse();
  const option = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 120, right: 24, top: 24, bottom: 32 },
    xAxis: { type: "value", name: "DHD" },
    yAxis: { type: "category", data: entries.map(([label]) => label) },
    series: [
      {
        type: "bar",
        data: entries.map(([, value]) => Number(value.toFixed(2))),
        itemStyle: { color: "#2f8f83" }
      }
    ]
  };
  return <ReactECharts option={option} style={{ height: 320, width: "100%" }} />;
}

