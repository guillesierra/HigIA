import type {
  AnomalyRecord,
  ATCCode,
  ConsumptionRecord,
  CorrelationPair,
  Drug,
  ExportSummary,
  RelationshipResponse,
  Relationships,
  SafetyAlert,
  Source,
  StudyDocument,
  TrendResult
} from "../types/domain";

const DATA_BASE = `${import.meta.env.BASE_URL}data`;

async function fetchStatic<T>(name: string): Promise<T> {
  try {
    const response = await fetch(`${DATA_BASE}/${name}.json`, { cache: "no-cache" });
    if (!response.ok) throw new Error(`Static data request failed: ${response.status}`);
    return response.json();
  } catch {
    return [] as unknown as T;
  }
}

async function loadAll() {
  const [sources, alerts, consumption, studies, drugs, atc, relationships] = await Promise.all([
    fetchStatic<Source[]>("sources"),
    fetchStatic<SafetyAlert[]>("alerts"),
    fetchStatic<ConsumptionRecord[]>("consumption"),
    fetchStatic<StudyDocument[]>("studies"),
    fetchStatic<Drug[]>("drugs"),
    fetchStatic<ATCCode[]>("atc"),
    fetchStatic<Relationships>("relationships"),
  ]);
  return { sources, alerts, consumption, studies, drugs, atc, relationships };
}

function pearsonR(x: number[], y: number[]): number {
  const n = x.length;
  if (n < 3) return 0;
  const xm = x.reduce((a, b) => a + b, 0) / n;
  const ym = y.reduce((a, b) => a + b, 0) / n;
  let num = 0, xd = 0, yd = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - xm, dy = y[i] - ym;
    num += dx * dy; xd += dx * dx; yd += dy * dy;
  }
  const den = Math.sqrt(xd * yd);
  return den === 0 ? 0 : num / den;
}

function computeRealCorrelations(consumption: ConsumptionRecord[]): CorrelationPair[] {
  // Group by (geography, atc_code) to get series
  const seriesMap = new Map<string, Map<number, number>>();
  consumption.forEach((r) => {
    if (!r.atc_code) return;
    const key = `${r.geography}|${r.atc_code}`;
    if (!seriesMap.has(key)) seriesMap.set(key, new Map());
    seriesMap.get(key)!.set(r.year, (seriesMap.get(key)!.get(r.year) ?? 0) + Number(r.dhd || 0));
  });

  // Build list of series with their year-value maps
  const entries = [...seriesMap.entries()].filter(([, m]) => m.size >= 3);
  const results: CorrelationPair[] = [];

  // Compare ALL pairs but limit to avoid explosion
  const max = Math.min(entries.length, 40);
  for (let i = 0; i < max; i++) {
    for (let j = i + 1; j < max; j++) {
      const [ka, va] = entries[i]; const [kb, vb] = entries[j];
      const common = [...va.keys()].filter(y => vb.has(y)).sort();
      if (common.length < 3) continue;
      const av = common.map(y => va.get(y)!);
      const bv = common.map(y => vb.get(y)!);
      const r = pearsonR(av, bv);
      if (Math.abs(r) > 0.01) {
        results.push({ entity_a: ka, entity_b: kb, correlation: Number(r.toFixed(4)), common_years: common.length });
      }
    }
  }
  return results.sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation)).slice(0, 40);
}

export const api = {
  sources: () => fetchStatic<Source[]>("sources"),
  alerts: () => fetchStatic<SafetyAlert[]>("alerts"),
  consumption: () => fetchStatic<ConsumptionRecord[]>("consumption"),
  studies: () => fetchStatic<StudyDocument[]>("studies"),
  drugs: () => fetchStatic<Drug[]>("drugs"),
  atc: () => fetchStatic<ATCCode[]>("atc"),
  relationships: () => fetchStatic<Relationships>("relationships"),
  trends: () => fetchStatic<TrendResult[]>("trends"),
  correlations: () => fetchStatic<CorrelationPair[]>("correlations"),
  anomalies: () => fetchStatic<AnomalyRecord[]>("anomalies"),
  summary: () => fetchStatic<ExportSummary>("summary"),
  correlationsCompute: (consumption: ConsumptionRecord[]) => computeRealCorrelations(consumption),
  all: loadAll,
  relationship: async (kind: "drug" | "atc" | "alert", query: string): Promise<RelationshipResponse> => {
    const data = await loadAll();
    return buildRelationship(kind, query, data);
  },
};

function buildRelationship(
  kind: "drug" | "atc" | "alert",
  query: string,
  data: Awaited<ReturnType<typeof loadAll>>
): RelationshipResponse {
  const lowered = query.trim().toLowerCase();
  if (!lowered) return { query, drugs: [], atc_codes: [], alerts: [], consumption: [], studies: [], sources: [] };

  const matchingAtc = data.atc.filter((item) => item.code.toLowerCase().startsWith(lowered) || item.name.toLowerCase().includes(lowered));
  const matchingDrugs = data.drugs.filter((item) =>
    `${item.name} ${item.active_ingredient ?? ""} ${item.normalized_name}`.toLowerCase().includes(lowered)
  );
  const atcIds = new Set(matchingAtc.map((item) => item.id));
  const drugIds = new Set(matchingDrugs.map((item) => item.id));

  if (kind === "atc") data.relationships.drug_atc.filter((item) => atcIds.has(item.atc_code_id)).forEach((item) => drugIds.add(item.drug_id));
  if (kind === "drug") data.relationships.drug_atc.filter((item) => drugIds.has(item.drug_id)).forEach((item) => atcIds.add(item.atc_code_id));

  const atcCodes = data.atc.filter((item) => atcIds.has(item.id) || (kind === "atc" && item.code.toLowerCase().startsWith(lowered)));
  const drugs = data.drugs.filter((item) => drugIds.has(item.id) || (kind === "drug" && item.name.toLowerCase().includes(lowered)));
  const atcPrefixes = atcCodes.map((item) => item.code.toLowerCase());
  const drugTerms = drugs.map((item) => `${item.name} ${item.active_ingredient ?? ""}`.toLowerCase());

  const alerts = data.alerts.filter((alert) => {
    if (kind === "alert") return String(alert.id) === lowered || `${alert.title} ${alert.summary ?? ""}`.toLowerCase().includes(lowered);
    return `${alert.title} ${alert.summary ?? ""} ${alert.raw_text ?? ""}`.toLowerCase().includes(lowered) ||
      data.relationships.alert_drugs.some((link) => link.alert_id === alert.id && ((link.drug_id && drugIds.has(link.drug_id)) || (link.atc_code_id && atcIds.has(link.atc_code_id))));
  });

  const consumption = data.consumption.filter((record) => {
    const rowText = `${record.atc_code ?? ""} ${record.drug_name ?? ""} ${record.active_ingredient ?? ""}`.toLowerCase();
    return rowText.includes(lowered) || atcPrefixes.some((prefix) => record.atc_code?.toLowerCase().startsWith(prefix)) || drugTerms.some((term) => term && rowText.includes(term));
  });

  const studies = data.studies.filter((study) => {
    const text = `${study.title} ${study.summary ?? ""} ${study.therapeutic_group ?? ""}`.toLowerCase();
    return text.includes(lowered) || data.relationships.study_drugs.some((link) => link.study_id === study.id && ((link.drug_id && drugIds.has(link.drug_id)) || (link.atc_code_id && atcIds.has(link.atc_code_id))));
  });

  const sourceIds = new Set([
    ...alerts.map((item) => item.source_id),
    ...consumption.map((item) => item.source_id),
    ...studies.map((item) => item.source_id).filter((id): id is number => typeof id === "number"),
  ]);

  return { query, drugs, atc_codes: atcCodes, alerts, consumption, studies, sources: data.sources.filter((source) => sourceIds.has(source.id)) };
}
