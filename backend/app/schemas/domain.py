from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceBase(BaseModel):
    name: str
    url: str
    source_type: str = "web"
    license: str | None = None
    notes: str | None = None


class SourceCreate(SourceBase):
    accessed_at: datetime | None = None


class SourceRead(SourceBase, ORMModel):
    id: int
    accessed_at: datetime


class DrugBase(BaseModel):
    name: str
    active_ingredient: str | None = None
    normalized_name: str


class DrugRead(DrugBase, ORMModel):
    id: int


class ATCCodeBase(BaseModel):
    code: str
    level: int | None = None
    name: str
    parent_code: str | None = None


class ATCCodeRead(ATCCodeBase, ORMModel):
    id: int


class SafetyAlertBase(BaseModel):
    source_id: int
    title: str
    date: date | None = None
    url: str
    organization: str | None = None
    alert_type: str | None = None
    summary: str | None = None
    raw_text: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    accessed_at: datetime | None = None
    raw_file_path: str | None = None
    parser_version: str | None = None


class SafetyAlertRead(SafetyAlertBase, ORMModel):
    id: int


class ConsumptionRecordBase(BaseModel):
    source_id: int
    source_name: str | None = None
    source_url: str | None = None
    accessed_at: datetime | None = None
    raw_file_path: str | None = None
    parser_version: str | None = None
    year: int
    month: int | None = Field(default=None, ge=1, le=12)
    geography: str
    geography_type: str
    population_group: str | None = None
    sector: str | None = None
    category: str | None = None
    atc_code: str | None = None
    drug_name: str | None = None
    active_ingredient: str | None = None
    packages: Decimal | None = None
    ddd: Decimal | None = None
    dhd: Decimal | None = None
    amount_pvpiva: Decimal | None = None
    unit: str | None = None
    notes: str | None = None


class ConsumptionRecordRead(ConsumptionRecordBase, ORMModel):
    id: int


class StudyDocumentBase(BaseModel):
    source_id: int | None = None
    title: str
    authors: str | None = None
    year: int | None = None
    url: str | None = None
    document_type: str | None = None
    geography: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    summary: str | None = None
    conclusions: str | None = None
    pending_work: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    accessed_at: datetime | None = None
    raw_file_path: str | None = None
    parser_version: str | None = None
    therapeutic_group: str | None = None


class StudyDocumentRead(StudyDocumentBase, ORMModel):
    id: int


class ComparisonResponse(BaseModel):
    alert_id: int
    alert_title: str
    alert_year: int | None
    metric: str
    before_average: float | None
    after_average: float | None
    before_records: int
    after_records: int
    delta: float | None
    filters: dict[str, str | int | None]


class RelationshipResponse(BaseModel):
    query: str
    drugs: list[DrugRead] = []
    atc_codes: list[ATCCodeRead] = []
    alerts: list[SafetyAlertRead] = []
    consumption: list[ConsumptionRecordRead] = []
    studies: list[StudyDocumentRead] = []
    sources: list[SourceRead] = []
