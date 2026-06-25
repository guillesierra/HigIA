import ReactECharts from "echarts-for-react";
import type { ConsumptionRecord } from "../types/domain";
import { getAtcName } from "../services/labels";

export function RankingChart({ records }: { records: ConsumptionRecord[] }) {
  const totals = new Map<string, number>();
  records.forEach((record) => {
    let label: string;
    if (record.atc_code && record.drug_name) {
      label = `${getAtcName(record.atc_code)} (${record.atc_code})`;
    } else {
      label = record.drug_name || record.atc_code || "Desconocido";
    }
    totals.set(label, (totals.get(label) ?? 0) + Number(record.dhd ?? 0));
  });
  const entries = Array.from(totals.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .reverse();
  const option = {
    title: { text: "DHD acumulado por grupo", left: "center", textStyle: { fontSize: 12, color: "#42505a" } },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (p: { data: { value: number }; axisValue: string }[]) => `${p[0]?.axisValue}: <b>${p[0]?.data?.value?.toFixed(2)} DHD</b>`,
    },
    grid: { left: 170, right: 40, top: 48, bottom: 35 },
    xAxis: { type: "value", name: "DHD (Dosis por Habitante y Día)", nameLocation: "middle", nameGap: 28 },
    yAxis: {
      type: "category",
      data: entries.map(([label]) => label),
      axisLabel: { fontSize: 10, width: 150, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        data: entries.map(([, value]) => ({ value: Number(value.toFixed(2)), itemStyle: { color: "#2f8f83" } })),
        label: { show: true, position: "right", formatter: "{c}", fontSize: 10 },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 340, width: "100%" }} />;
}
