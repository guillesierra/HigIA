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
        { key: "date", label: "Fecha", render: (row) => row.date?.slice(0, 10) ?? "-" },
        {
          key: "title",
          label: "Alerta",
          render: (row) => (
            <button className={row.id === selectedId ? "table-button selected" : "table-button"} onClick={() => onSelect(row)}>
              <span style={{ color: "#c62828", fontWeight: 500, fontSize: 13 }}>
                {row.summary ? row.summary.slice(0, 140) + (row.summary.length > 140 ? "…" : "") : row.title.slice(0, 120)}
              </span>
            </button>
          )
        },
        { key: "org", label: "Organismo", render: (row) => row.organization ?? "AEMPS" },
        { key: "type", label: "Tipo", render: (row) => row.alert_type ?? "Seguridad" },
        { key: "ingredients", label: "Principios activos", render: (row) => row.possible_active_ingredients?.slice(0, 4).join(", ") || "—" },
      ]}
    />
  );
}
