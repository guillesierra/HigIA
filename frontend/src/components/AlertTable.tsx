import { AlertTriangle, Calendar, ExternalLink, Pill, Shield } from "lucide-react";
import { DataTable } from "./DataTable";
import { EmptyState } from "./Status";
import type { SafetyAlert } from "../types/domain";

function extractKeyPoints(alert: SafetyAlert): string[] {
  const text = `${alert.raw_text ?? ""} ${alert.summary ?? ""}`;
  if (!text.trim()) return [];
  const points: string[] = [];

  // Extract meaningful sentences
  const sentences = text.split(/[.;]\s+/).map(s => s.trim()).filter(s => s.length > 20 && s.length < 300);

  // Look for key patterns
  for (const s of sentences.slice(0, 30)) {
    const lower = s.toLowerCase();
    if (
      lower.includes("riesgo") || lower.includes("reacción") || lower.includes("advers") ||
      lower.includes("contraindic") || lower.includes("suspensión") || lower.includes("retirada") ||
      lower.includes("restricción") || lower.includes("recomienda") || lower.includes("precaución") ||
      lower.includes("interacción") || lower.includes("dosis máxima") || lower.includes("no utilizar") ||
      lower.includes("vigilancia") || lower.includes("farmacovigilancia") || lower.includes("muerte") ||
      lower.includes("hospitaliz") || lower.includes("grave") || lower.includes("nuevo hallazgo") ||
      lower.includes("alerta")
    ) {
      points.push(s);
    }
  }

  // If no specific points found, fall back to first meaningful sentences
  if (!points.length) {
    return sentences.slice(0, 5).map(s => s.charAt(0).toUpperCase() + s.slice(1) + ".");
  }

  return points.slice(0, 6).map(s => s.charAt(0).toUpperCase() + s.slice(1) + ".");
}

function getAlertCategory(rawText: string | null | undefined): string {
  const text = (rawText ?? "").toLowerCase();
  if (text.includes("antibiótico") || text.includes("antibacterial")) return "Antibióticos";
  if (text.includes("aine") || text.includes("antiinflamatorio") || text.includes("ibuprofeno") || text.includes("naproxeno")) return "AINEs";
  if (text.includes("opiáceo") || text.includes("opioide") || text.includes("morfina") || text.includes("fentanilo") || text.includes("tramadol")) return "Opioides";
  if (text.includes("estatina") || text.includes("atorvastatina") || text.includes("simvastatina")) return "Estatinas";
  if (text.includes("antidepresivo") || text.includes("isrs") || text.includes("fluoxetina") || text.includes("sertralina")) return "Antidepresivos";
  if (text.includes("benzodiacepina") || text.includes("diazepam") || text.includes("lorazepam")) return "Benzodiacepinas";
  if (text.includes("anticoagulante") || text.includes("antivitamina k") || text.includes("warfarin") || text.includes("acenocumarol") || text.includes("doac")) return "Anticoagulantes";
  if (text.includes("antidiabético") || text.includes("metformina") || text.includes("insulina")) return "Antidiabéticos";
  if (text.includes("ibp") || text.includes("omeprazol") || text.includes("pantoprazol")) return "IBPs";
  if (text.includes("vacuna")) return "Vacunas";
  if (text.includes("antipsicótico") || text.includes("risperidona") || text.includes("olanzapina")) return "Antipsicóticos";
  if (text.includes("anticancer") || text.includes("antineoplásico") || text.includes("quimioterapia")) return "Antineoplásicos";
  if (text.includes("antihipertensivo") || text.includes("ieca") || text.includes("ara-ii") || text.includes("enalapril") || text.includes("losartán")) return "Antihipertensivos";
  return "General";
}

export function AlertTable({ alerts, selectedId, onSelect }: { alerts: SafetyAlert[]; selectedId?: number | null; onSelect: (a: SafetyAlert) => void }) {
  if (!alerts.length) return <EmptyState message="No hay alertas que coincidan con los filtros." />;

  return (
    <DataTable
      rows={alerts}
      columns={[
        { key: "date", label: "Fecha", render: (row) => row.date?.slice(0, 10) ?? "-" },
        {
          key: "alert",
          label: "Alerta",
          render: (row) => {
            const points = extractKeyPoints(row);
            const category = getAlertCategory(row.raw_text);
            return (
              <button className={row.id === selectedId ? "table-button selected" : "table-button"} onClick={() => onSelect(row)} style={{ textAlign: "left" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  <span style={{ color: "#c62828", fontWeight: 600, fontSize: 13 }}>{row.title.slice(0, 120)}</span>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <span className="tag">{category}</span>
                    {row.possible_active_ingredients?.slice(0, 3).map((ing) => (
                      <span key={ing} className="tag" style={{ background: "#fbe9e7", color: "#8b3a2a" }}>{ing}</span>
                    ))}
                  </div>
                  {points.length > 0 && (
                    <ul style={{ margin: "4px 0 0", paddingLeft: 16, fontSize: 12, color: "#42505a", lineHeight: 1.5 }}>
                      {points.slice(0, 3).map((p, i) => <li key={i}>{p.slice(0, 150)}</li>)}
                    </ul>
                  )}
                </div>
              </button>
            );
          }
        },
        { key: "org", label: "Organismo", render: (row) => row.organization ?? "AEMPS" },
        { key: "type", label: "Tipo", render: (row) => row.alert_type ?? "Seguridad" },
      ]}
    />
  );
}
