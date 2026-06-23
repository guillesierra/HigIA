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
