import { DataTable } from "./DataTable";
import { EmptyState } from "./Status";
import type { ConsumptionRecord } from "../types/domain";

export function ConsumptionTable({ records }: { records: ConsumptionRecord[] }) {
  if (!records.length) return <EmptyState message="No hay registros de consumo que coincidan con los filtros." />;

  return (
    <DataTable
      rows={records}
      columns={[
        { key: "year", label: "Ano", render: (row) => row.year },
        { key: "geo", label: "Geografia", render: (row) => row.geography },
        { key: "sector", label: "Sector", render: (row) => row.sector ?? "-" },
        { key: "atc", label: "ATC", render: (row) => row.atc_code ?? row.category ?? "-" },
        { key: "drug", label: "Medicamento", render: (row) => row.drug_name ?? row.active_ingredient ?? "-" },
        { key: "dhd", label: "DHD", render: (row) => row.dhd ?? "-" },
        { key: "packages", label: "Envases", render: (row) => row.packages ?? "-" }
      ]}
    />
  );
}

