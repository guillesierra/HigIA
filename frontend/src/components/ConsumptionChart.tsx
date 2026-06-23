import { TimeSeriesChart } from "../charts/TimeSeriesChart";
import { EmptyState } from "./Status";
import type { ConsumptionRecord } from "../types/domain";

export function ConsumptionChart({ records }: { records: ConsumptionRecord[] }) {
  if (!records.length) return <EmptyState message="No hay datos de consumo para la grafica." />;
  return <TimeSeriesChart records={records} />;
}

