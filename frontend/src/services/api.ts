import type {
  ATCCode,
  ConsumptionRecord,
  Drug,
  RelationshipResponse,
  Relationships,
  SafetyAlert,
  Source,
  StudyDocument
} from "../types/domain";

const DATA_BASE = `${import.meta.env.BASE_URL}data`;

const mockSources: Source[] = [
  {
    id: 1,
    name: "AEMPS medicine safety notes",
    url: "https://www.aemps.gob.es/",
    source_type: "official_web",
    license: "Check source terms before redistribution",
    accessed_at: "2026-06-23T00:00:00",
    notes: "Mock source used when static JSON is not available.",
    status: "mock"
  }
];

const mockAlerts: SafetyAlert[] = [
  {
    id: 1,
    source_id: 1,
    title: "Example safety note related to benzodiazepine risk minimization",
    date: "2021-06-15",
    url: "https://www.aemps.gob.es/",
    organization: "AEMPS",
    alert_type: "Safety",
    summary: "Mock alert for local static rendering.",
    raw_text: "Diazepam N05BA mock text.",
    possible_active_ingredients: ["diazepam"]
  }
];

const mockConsumption: ConsumptionRecord[] = [
  {
    id: 1,
    source_id: 1,
    year: 2023,
    geography: "Asturias",
    geography_type: "autonomous_community",
    atc_code: "J01CA",
    drug_name: "Amoxicillin",
    active_ingredient: "amoxicillin",
    packages: 42000,
    ddd: null,
    dhd: 11.9,
    amount_pvpiva: null,
    unit: "DHD",
    notes: "Mock aggregated record."
  }
];

const mockStudies: StudyDocument[] = [
  {
    id: 1,
    source_id: 1,
    title: "Demo Asturias public document inventory for medicine use",
    year: 2024,
    url: "https://www.astursalud.es/",
    document_type: "public_document_inventory",
    geography: "Asturias",
    summary: "Mock document used when exported studies JSON is not available.",
    pending_work: "Review public PDFs before structured extraction.",
    therapeutic_group: "antibiotics"
  }
];

const mockDrugs: Drug[] = [
  { id: 1, name: "Amoxicillin", active_ingredient: "amoxicillin", normalized_name: "amoxicillin" },
  { id: 2, name: "Diazepam", active_ingredient: "diazepam", normalized_name: "diazepam" }
];

const mockAtc: ATCCode[] = [
  { id: 1, code: "J01CA", level: 4, name: "Penicillins with extended spectrum", parent_code: "J01" },
  { id: 2, code: "N05BA", level: 4, name: "Benzodiazepine derivatives", parent_code: "N05B" }
];

const mockRelationships: Relationships = {
  drug_atc: [{ drug_id: 1, atc_code_id: 1 }],
  alert_drugs: [{ alert_id: 1, drug_id: 2, atc_code_id: 2 }],
  study_drugs: [{ study_id: 1, drug_id: 1, atc_code_id: 1 }],
  atc_consumption: [{ atc_code: "J01CA", consumption_record_id: 1, drug_name: "Amoxicillin", year: 2023, geography: "Asturias" }]
};

const fallbacks = {
  sources: mockSources,
  alerts: mockAlerts,
  consumption: mockConsumption,
  studies: mockStudies,
  drugs: mockDrugs,
  atc: mockAtc,
  relationships: mockRelationships
};

async function fetchStatic<T>(name: keyof typeof fallbacks): Promise<T> {
  try {
    const response = await fetch(`${DATA_BASE}/${name}.json`, { cache: "no-cache" });
    if (!response.ok) throw new Error(`Static data request failed: ${response.status}`);
    return response.json();
  } catch {
    // Static JSON is the production data path; mocks keep the UI usable before the first export.
    return fallbacks[name] as T;
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
    fetchStatic<Relationships>("relationships")
  ]);
  return { sources, alerts, consumption, studies, drugs, atc, relationships };
}

export const api = {
  sources: () => fetchStatic<Source[]>("sources"),
  alerts: () => fetchStatic<SafetyAlert[]>("alerts"),
  consumption: () => fetchStatic<ConsumptionRecord[]>("consumption"),
  studies: () => fetchStatic<StudyDocument[]>("studies"),
  drugs: () => fetchStatic<Drug[]>("drugs"),
  atc: () => fetchStatic<ATCCode[]>("atc"),
  relationships: () => fetchStatic<Relationships>("relationships"),
  all: loadAll,
  relationship: async (kind: "drug" | "atc" | "alert", query: string): Promise<RelationshipResponse> => {
    const data = await loadAll();
    return buildRelationship(kind, query, data);
  }
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

  if (kind === "atc") {
    data.relationships.drug_atc.filter((item) => atcIds.has(item.atc_code_id)).forEach((item) => drugIds.add(item.drug_id));
  }
  if (kind === "drug") {
    data.relationships.drug_atc.filter((item) => drugIds.has(item.drug_id)).forEach((item) => atcIds.add(item.atc_code_id));
  }

  const atcCodes = data.atc.filter((item) => atcIds.has(item.id) || (kind === "atc" && item.code.toLowerCase().startsWith(lowered)));
  const drugs = data.drugs.filter((item) => drugIds.has(item.id) || (kind === "drug" && item.name.toLowerCase().includes(lowered)));
  const atcPrefixes = atcCodes.map((item) => item.code.toLowerCase());
  const drugTerms = drugs.map((item) => `${item.name} ${item.active_ingredient ?? ""}`.toLowerCase());

  const alerts = data.alerts.filter((alert) => {
    if (kind === "alert") return String(alert.id) === lowered || `${alert.title} ${alert.summary ?? ""}`.toLowerCase().includes(lowered);
    return (
      `${alert.title} ${alert.summary ?? ""} ${alert.raw_text ?? ""}`.toLowerCase().includes(lowered) ||
      data.relationships.alert_drugs.some((link) => link.alert_id === alert.id && ((link.drug_id && drugIds.has(link.drug_id)) || (link.atc_code_id && atcIds.has(link.atc_code_id))))
    );
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
    ...studies.map((item) => item.source_id).filter((id): id is number => typeof id === "number")
  ]);

  return {
    query,
    drugs,
    atc_codes: atcCodes,
    alerts,
    consumption,
    studies,
    sources: data.sources.filter((source) => sourceIds.has(source.id))
  };
}

