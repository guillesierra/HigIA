export type Source = {
  id: number;
  name: string;
  url: string;
  source_type: string;
  license?: string | null;
  accessed_at: string;
  notes?: string | null;
  status?: string | null;
};

export type Drug = {
  id: number;
  name: string;
  active_ingredient?: string | null;
  normalized_name: string;
};

export type ATCCode = {
  id: number;
  code: string;
  level?: number | null;
  name: string;
  parent_code?: string | null;
};

export type SafetyAlert = {
  id: number;
  source_id: number;
  title: string;
  date?: string | null;
  url: string;
  organization?: string | null;
  alert_type?: string | null;
  summary?: string | null;
  raw_text?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  accessed_at?: string | null;
  raw_file_path?: string | null;
  parser_version?: string | null;
  possible_active_ingredients?: string[];
};

export type ConsumptionRecord = {
  id: number;
  source_id: number;
  source_name?: string | null;
  source_url?: string | null;
  accessed_at?: string | null;
  raw_file_path?: string | null;
  parser_version?: string | null;
  year: number;
  month?: number | null;
  geography: string;
  geography_type: string;
  population_group?: string | null;
  sector?: string | null;
  category?: string | null;
  atc_code?: string | null;
  drug_name?: string | null;
  active_ingredient?: string | null;
  packages?: number | null;
  ddd?: number | null;
  dhd?: number | null;
  amount_pvpiva?: number | null;
  unit?: string | null;
  notes?: string | null;
};

export type StudyDocument = {
  id: number;
  source_id?: number | null;
  title: string;
  authors?: string | null;
  year?: number | null;
  url?: string | null;
  document_type?: string | null;
  geography?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  summary?: string | null;
  conclusions?: string | null;
  pending_work?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  accessed_at?: string | null;
  raw_file_path?: string | null;
  parser_version?: string | null;
  therapeutic_group?: string | null;
  keywords?: string[];
};

export type RelationshipResponse = {
  query: string;
  drugs: Drug[];
  atc_codes: ATCCode[];
  alerts: SafetyAlert[];
  consumption: ConsumptionRecord[];
  studies: StudyDocument[];
  sources: Source[];
};

export type Relationships = {
  drug_atc: Array<{ drug_id: number; atc_code_id: number }>;
  alert_drugs: Array<{ id?: number; alert_id: number; drug_id?: number | null; atc_code_id?: number | null }>;
  study_drugs: Array<{ id?: number; study_id: number; drug_id?: number | null; atc_code_id?: number | null }>;
  atc_consumption: Array<{
    atc_code: string;
    consumption_record_id: number;
    drug_name?: string | null;
    year?: number | null;
    geography?: string | null;
  }>;
};

export type ComparisonResponse = {
  alert_id: number;
  alert_title: string;
  alert_year?: number | null;
  metric: string;
  before_average?: number | null;
  after_average?: number | null;
  before_records: number;
  after_records: number;
  delta?: number | null;
  filters: Record<string, string | number | null>;
};

export type TrendResult = {
  entity_key: string;
  metric: string;
  slope: number;
  mean_value: number;
  total_change: number;
  avg_yoy_change: number;
  trend_direction: "increasing" | "decreasing" | "stable";
  years: number[];
  values: number[];
  start_value: number | null;
  end_value: number | null;
};

export type CorrelationPair = {
  entity_a: string;
  entity_b: string;
  correlation: number;
  common_years: number;
};

export type AnomalyRecord = {
  entity_key: string;
  year: number;
  previous_year: number;
  value: number;
  previous_value: number;
  change_pct: number;
  direction: "spike" | "drop";
};

export type ImpactResult = {
  entity_key: string;
  avg_before: number;
  avg_after: number;
  change_pct: number;
  direction: string;
  overall_mean: number;
};

export type YearOverYear = {
  entity_key: string;
  year: number;
  previous_year: number;
  value: number;
  previous_value: number;
  change_pct: number;
  direction: "up" | "down" | "flat";
};

export type GeoComparison = {
  geography: string;
  codes: Array<{
    atc_code: string;
    avg_value: number;
    record_count: number;
  }>;
};

export type SummaryStats = {
  total_records: number;
  avg_value: number | null;
  max_value: number | null;
  min_value: number | null;
  median: number | null;
  stdev: number;
  year_range: { min: number; max: number } | null;
  distinct_geographies: number;
};

export type ValidationReport = {
  source_name: string;
  summary: {
    source_name: string;
    run_at: string;
    total_records: number;
    consumption_records: number;
    alert_records: number;
    study_records: number;
    error_records: number;
  };
  consumption_validation?: {
    total_records: number;
    valid_records: number;
    missing_year: number;
    missing_geography: number;
    missing_atc_code: number;
    missing_dhd: number;
    out_of_range_dhd: number;
    duplicate_keys: number;
    year_range: [number, number] | null;
    geographies: string[];
    atc_codes_found: string[];
    dhd_stats: Record<string, number>;
    field_completeness: Record<string, number>;
  };
  alert_validation?: {
    total_records: number;
    valid_records: number;
    missing_title: number;
    missing_date: number;
    missing_url: number;
    missing_summary: number;
    duplicate_urls: number;
    active_ingredients_found: number;
    organizations: string[];
  };
  duplicate_alerts: Array<{ title_a: string; title_b: string }>;
  duplicate_consumption: Array<{ title_a: string; title_b: string }>;
};

export type ExportSummary = {
  counts: {
    sources: number;
    alerts: number;
    consumption_records: number;
    studies: number;
    drugs: number;
    atc_codes: number;
  };
  year_range: { min: number; max: number } | null;
  top_geographies: Array<{ name: string; records: number }>;
  alerts_timeline: Array<{ year: number; count: number }>;
  generated_at: string;
};
