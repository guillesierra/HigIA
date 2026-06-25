import { ExternalLink } from "lucide-react";
import { DataTable } from "./DataTable";
import { EmptyState } from "./Status";
import type { Source } from "../types/domain";

type SourceRow = Source & { urlCount?: number };

export function SourceTable({ sources }: { sources: SourceRow[] }) {
  if (!sources.length) return <EmptyState message="No hay fuentes para mostrar." />;

  return (
    <DataTable
      rows={sources}
      columns={[
        { key: "name", label: "Fuente", render: (row) => <strong>{row.name}</strong> },
        { key: "type", label: "Tipo", render: (row) => row.source_type },
        { key: "status", label: "Estado", render: (row) => row.status ?? (row.notes ? "catalogada" : "pendiente") },
        { key: "accessed", label: "Acceso", render: (row) => formatDate(row.accessed_at) },
        { key: "urls", label: "URLs", render: (row) => row.urlCount ?? 1 },
        { key: "license", label: "Licencia / notas", render: (row) => row.license ?? row.notes ?? "Por revisar" },
        {
          key: "url",
          label: "URL",
          render: (row) => (
            <a className="icon-link" href={row.url} target="_blank" rel="noreferrer" title={row.url}>
              <ExternalLink size={16} />
              <span>abrir</span>
            </a>
          )
        }
      ]}
    />
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}
