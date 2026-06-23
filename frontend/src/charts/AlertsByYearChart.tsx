import ReactECharts from "echarts-for-react";
import type { SafetyAlert } from "../types/domain";

export function AlertsByYearChart({ alerts }: { alerts: SafetyAlert[] }) {
  const counts = new Map<number, number>();
  alerts.forEach((alert) => {
    if (!alert.date) return;
    const year = Number(alert.date.slice(0, 4));
    if (!Number.isNaN(year)) counts.set(year, (counts.get(year) ?? 0) + 1);
  });
  const entries = Array.from(counts.entries()).sort((a, b) => a[0] - b[0]);
  const option = {
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 20, top: 24, bottom: 40 },
    xAxis: { type: "category", data: entries.map(([year]) => year) },
    yAxis: { type: "value" },
    series: [
      {
        type: "bar",
        data: entries.map(([, count]) => count),
        itemStyle: { color: "#b45f3b" }
      }
    ]
  };
  return <ReactECharts option={option} style={{ height: 260, width: "100%" }} />;
}

