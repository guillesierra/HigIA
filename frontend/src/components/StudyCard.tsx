import { ExternalLink } from "lucide-react";
import type { StudyDocument } from "../types/domain";

export function StudyCard({ study }: { study: StudyDocument }) {
  return (
    <article className="study-card">
      <div>
        <span className="tag">{study.document_type ?? "documento"}</span>
        {study.therapeutic_group ? <span className="tag secondary">{study.therapeutic_group}</span> : null}
      </div>
      <h3>{study.title}</h3>
      <p>{study.summary ?? study.pending_work ?? "Sin resumen estructurado."}</p>
      <footer>
        <span>{[study.geography, study.year].filter(Boolean).join(" | ") || "Ambito por revisar"}</span>
        {study.url ? (
          <a href={study.url} target="_blank" rel="noreferrer" title={study.url}>
            <ExternalLink size={15} />
          </a>
        ) : null}
      </footer>
    </article>
  );
}

