import { TimeSeriesChart } from "../charts/TimeSeriesChart";
import { EmptyState } from "./Status";
import type { ConsumptionRecord } from "../types/domain";

type Props = {
  records: ConsumptionRecord[];
  metric?: "dhd" | "ddd" | "packages" | "amount_pvpiva";
  maxSeries?: number;
};

export function ConsumptionChart({ records, metric = "dhd", maxSeries }: Props) {
  if (!records.length) return <EmptyState message="No hay datos de consumo para la gráfica." />;
  return <TimeSeriesChart records={records} metric={metric} maxSeries={maxSeries} />;
}
