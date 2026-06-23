import { DataTable } from "./DataTable";
import { EmptyState } from "./Status";
import type { SafetyAlert } from "../types/domain";

type AlertTableProps = {
  alerts: SafetyAlert[];
  selectedId?: number | null;
  onSelect: (alert: SafetyAlert) => void;
};

export function AlertTable({ alerts, selectedId, onSelect }: AlertTableProps) {
  if (!alerts.length) return <EmptyState message="No hay alertas que coincidan con los filtros." />;

  return (
    <DataTable
      rows={alerts}
      columns={[
        { key: "date", label: "Fecha", render: (row) => row.date ?? "-" },
        {
          key: "title",
          label: "Titulo",
          render: (row) => (
            <button className={row.id === selectedId ? "table-button selected" : "table-button"} onClick={() => onSelect(row)}>
              {row.title}
            </button>
          )
        },
        { key: "org", label: "Org.", render: (row) => row.organization ?? "-" },
        { key: "type", label: "Tipo", render: (row) => row.alert_type ?? "-" },
        { key: "ingredients", label: "Principios", render: (row) => row.possible_active_ingredients?.join(", ") || "-" }
      ]}
    />
  );
}

