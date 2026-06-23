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
    title: { text: "N.º de alertas de seguridad por año", left: "center", textStyle: { fontSize: 12, color: "#42505a" } },
    tooltip: { trigger: "axis", formatter: (p: { data: number; axisValue: string }[]) => `Año ${p[0]?.axisValue}: <b>${p[0]?.data} alertas</b>` },
    grid: { left: 48, right: 20, top: 50, bottom: 45 },
    xAxis: { type: "category", data: entries.map(([year]) => year), name: "Año", nameLocation: "middle", nameGap: 30 },
    yAxis: { type: "value", name: "N.º de alertas", nameLocation: "middle", nameGap: 38 },
    series: [
      {
        type: "bar",
        data: entries.map(([, count]) => count),
        itemStyle: { color: "#b45f3b" },
        label: { show: true, position: "top", fontSize: 11 },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 300, width: "100%" }} />;
}
