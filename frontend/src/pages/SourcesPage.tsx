import { useEffect, useMemo, useState } from "react";
import { FilterPanel } from "../components/FilterPanel";
import { LoadingState } from "../components/Status";
import { SourceTable } from "../components/SourceTable";
import { api } from "../services/api";
import type { Source } from "../types/domain";

export function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.sources().then(setSources).finally(() => setLoading(false));
  }, []);

  const types = Array.from(new Set(sources.map((source) => source.source_type))).sort();
  const rows = useMemo(
    () =>
      sources.filter((source) => {
        const haystack = `${source.name} ${source.url} ${source.source_type} ${source.license ?? ""} ${source.notes ?? ""}`.toLowerCase();
        return haystack.includes(query.toLowerCase()) && (!type || source.source_type === type);
      }),
    [sources, query, type]
  );

  if (loading) return <LoadingState />;

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Provenance</p>
          <h1>Fuentes</h1>
        </div>
      </header>

      <FilterPanel>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar fuente, URL o notas" />
        <select value={type} onChange={(event) => setType(event.target.value)}>
          <option value="">Todos los tipos</option>
          {types.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </FilterPanel>

      <SourceTable sources={rows} />
    </div>
  );
}

