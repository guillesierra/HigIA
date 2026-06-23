import { DataTable } from "./DataTable";
import { EmptyState } from "./Status";
import type { ConsumptionRecord } from "../types/domain";
import { getAtcName } from "../services/labels";

export function ConsumptionTable({ records }: { records: ConsumptionRecord[] }) {
  if (!records.length) return <EmptyState message="No hay registros de consumo que coincidan con los filtros." />;

  return (
    <DataTable
      rows={records}
      columns={[
        { key: "year", label: "Año", render: (row) => row.year },
        { key: "month", label: "Mes", render: (row) => row.month ?? "—" },
        { key: "geo", label: "Comunidad", render: (row) => row.geography },
        { key: "sector", label: "Sector", render: (row) => row.sector ?? "—" },
        { key: "atc", label: "ATC", render: (row) => row.atc_code ? `${getAtcName(row.atc_code)} (${row.atc_code})` : (row.category ?? "—") },
        { key: "drug", label: "Medicamento", render: (row) => row.drug_name ?? row.active_ingredient ?? "—" },
        { key: "dhd", label: "DHD", render: (row) => row.dhd?.toLocaleString("es-ES") ?? "—" },
        { key: "ddd", label: "DDD", render: (row) => row.ddd?.toLocaleString("es-ES") ?? "—" },
        { key: "packages", label: "Envases", render: (row) => row.packages?.toLocaleString("es-ES") ?? "—" },
        { key: "amount", label: "PVP IVA (€)", render: (row) => row.amount_pvpiva != null ? `${Number(row.amount_pvpiva).toLocaleString("es-ES", { maximumFractionDigits: 0 })} €` : "—" },
      ]}
    />
  );
}
