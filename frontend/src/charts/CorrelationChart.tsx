import ReactECharts from "echarts-for-react";
import type { CorrelationPair } from "../types/domain";
import { getAtcName } from "../services/labels";

type Props = {
  correlations: CorrelationPair[];
};

export function CorrelationChart({ correlations }: Props) {
  if (!correlations.length) return <p className="muted">Datos insuficientes para correlaciones.</p>;

  const top = correlations.slice(0, 15);
  const labels = top.map((c) => {
    const a = `${getAtcName(c.entity_a)} (${c.entity_a})`;
    const b = `${getAtcName(c.entity_b)} (${c.entity_b})`;
    return { a, b, full: `${a.slice(0, 18)} vs ${b.slice(0, 18)}` };
  });

  const option = {
    title: { text: "Correlación entre grupos ATC (DHD)", left: "center", textStyle: { fontSize: 12, color: "#42505a" } },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: { dataIndex: number }[]) => {
        const i = params[0]?.dataIndex;
        if (i === undefined) return "";
        const c = top[i];
        const la = labels[i];
        return `<strong>${la.a}</strong><br/>vs <strong>${la.b}</strong><br/>
          Coeficiente Pearson (r): <b>${c.correlation}</b><br/>
          Años en común: ${c.common_years}<br/>
          <small>${c.correlation > 0.7 ? "Correlación positiva FUERTE" : c.correlation > 0.4 ? "Correlación positiva MODERADA" : c.correlation < -0.7 ? "Correlación negativa FUERTE" : c.correlation < -0.4 ? "Correlación negativa MODERADA" : "Correlación DÉBIL"}</small>`;
      },
    },
    grid: { left: 190, right: 60, top: 50, bottom: 32 },
    xAxis: {
      type: "value",
      name: "Coeficiente de Pearson (r)",
      nameLocation: "middle",
      nameGap: 25,
      min: -1,
      max: 1,
    },
    yAxis: {
      type: "category",
      data: labels.map((l) => l.full).reverse(),
      axisLabel: { fontSize: 10, width: 175, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        data: top
          .map((c) => ({
            value: c.correlation,
            itemStyle: {
              color: c.correlation > 0.7 ? "#1b5e50" : c.correlation > 0 ? "#2f8f83" : c.correlation < -0.7 ? "#8b3a2a" : "#b45f3b",
            },
          }))
          .reverse(),
        label: { show: true, position: "right", formatter: "{c}", fontSize: 10 },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 440, width: "100%" }} />;
}
