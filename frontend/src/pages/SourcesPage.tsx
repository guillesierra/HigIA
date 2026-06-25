import { useEffect, useMemo, useState } from "react";
import { FilterPanel } from "../components/FilterPanel";
import { LoadingState } from "../components/Status";
import { SourceTable } from "../components/SourceTable";
import { api } from "../services/api";
import type { Source } from "../types/domain";

type SourceGroup = Source & { urlCount: number };

export function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.sources().then(setSources).finally(() => setLoading(false));
  }, []);

  const sourceGroups = useMemo(() => {
    const grouped = new Map<string, SourceGroup>();
    sources.forEach((source) => {
      const key = [
        source.name,
        source.source_type,
        source.license ?? "",
        source.notes ?? "",
        source.status ?? "",
      ].join("|");
      const current = grouped.get(key);
      if (!current) {
        grouped.set(key, { ...source, urlCount: 1 });
        return;
      }
      current.urlCount += 1;
      if (new Date(source.accessed_at).getTime() > new Date(current.accessed_at).getTime()) {
        current.accessed_at = source.accessed_at;
        current.url = source.url;
        current.status = source.status;
      }
    });
    return [...grouped.values()].sort((a, b) => b.urlCount - a.urlCount || a.name.localeCompare(b.name));
  }, [sources]);

  const types = Array.from(new Set(sourceGroups.map((source) => source.source_type))).sort();
  const rows = useMemo(
    () =>
      sourceGroups.filter((source) => {
        const haystack =
          `${source.name} ${source.url} ${source.source_type} ${source.license ?? ""} ${source.notes ?? ""}`.toLowerCase();
        return haystack.includes(query.toLowerCase()) && (!type || source.source_type === type);
      }),
    [sourceGroups, query, type]
  );

  if (loading) return <LoadingState />;

  return (
    <div className="page">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">Provenance</p>
          <h1>Fuentes</h1>
          <p className="muted">
            {rows.length} fuentes agrupadas | {sources.length} URLs trazadas
          </p>
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
