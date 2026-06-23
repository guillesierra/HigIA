import { useEffect, useMemo, useState } from "react";
import { ConsumptionTable } from "../components/ConsumptionTable";
import { FilterPanel } from "../components/FilterPanel";
import { MetricStrip } from "../components/MetricStrip";
import { StudyCard } from "../components/StudyCard";
import { EmptyState, LoadingState } from "../components/Status";
import { api } from "../services/api";
import type { ConsumptionRecord, Source, StudyDocument } from "../types/domain";

export function AsturiasPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [studies, setStudies] = useState<StudyDocument[]>([]);
  const [consumption, setConsumption] = useState<ConsumptionRecord[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.sources(), api.studies(), api.consumption()])
      .then(([sourceRows, studyRows, consumptionRows]) => {
        setSources(sourceRows);
        setStudies(studyRows);
        setConsumption(consumptionRows);
      })
      .finally(() => setLoading(false));
  }, []);

  const asturiasSources = useMemo(() => sources.filter((source) => `${source.name} ${source.url}`.toLowerCase().includes("astur")), [sources]);
  const asturiasStudies = useMemo(
    () =>
      studies.filter((study) => {
        const text = `${study.geography ?? ""} ${study.title} ${study.summary ?? ""} ${study.therapeutic_group ?? ""}`.toLowerCase();
        return text.includes("astur") && text.includes(query.toLowerCase());
      }),
    [studies, query]
  );
  const asturiasConsumption = useMemo(
    () => consumption.filter((record) => record.geography.toLowerCase().includes("astur") && `${record.atc_code ?? ""} ${record.drug_name ?? ""}`.toLowerCase().includes(query.toLowerCase())),
    [consumption, query]
  );

  if (loading) return <LoadingState />;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Regional scope</p>
          <h1>Asturias</h1>
          <p>Documentacion publica, datasets agregados disponibles y huecos de datos identificados para una futura integracion autorizada.</p>
        </div>
      </header>

      <MetricStrip
        metrics={[
          { label: "Fuentes Asturias", value: asturiasSources.length, tone: "teal" },
          { label: "Documentos", value: asturiasStudies.length, tone: "rust" },
          { label: "Registros consumo", value: asturiasConsumption.length, tone: "ink" }
        ]}
      />

      <FilterPanel>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar documento, ATC o medicamento" />
      </FilterPanel>

      <section className="grid two">
        <div className="panel">
          <div className="panel-heading">
            <h2>Documentacion encontrada</h2>
          </div>
          <div className="study-list">
            {asturiasStudies.length ? asturiasStudies.map((study) => <StudyCard key={study.id} study={study} />) : <EmptyState message="No hay documentos con esos filtros." />}
          </div>
        </div>
        <div className="panel">
          <div className="panel-heading">
            <h2>Huecos y proximos pasos</h2>
          </div>
          <div className="availability">
            <p><strong>Datasets disponibles:</strong> solo registros agregados presentes en los JSON publicos.</p>
            <p><strong>Huecos:</strong> series internas SESPA, prescripcion detallada, poblaciones denominador y metadatos de metodologia no publicados.</p>
            <p><strong>SESPA:</strong> si se obtiene acceso, crear ingesta separada, validar permiso de publicacion y exportar solo agregados anonimos.</p>
          </div>
        </div>
      </section>

      <ConsumptionTable records={asturiasConsumption} />
    </div>
  );
}

