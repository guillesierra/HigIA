from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, default="web")
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    alerts: Mapped[list["SafetyAlert"]] = relationship(back_populates="source")
    consumption_records: Mapped[list["ConsumptionRecord"]] = relationship(back_populates="source")
    studies: Mapped[list["StudyDocument"]] = relationship(back_populates="source")


class Drug(Base):
    __tablename__ = "drugs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active_ingredient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    atc_links: Mapped[list["DrugATC"]] = relationship(back_populates="drug", cascade="all, delete-orphan")
    alert_links: Mapped[list["AlertDrug"]] = relationship(back_populates="drug")
    study_links: Mapped[list["StudyDrug"]] = relationship(back_populates="drug")


class ATCCode(Base):
    __tablename__ = "atc_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(16), nullable=True)

    drug_links: Mapped[list["DrugATC"]] = relationship(back_populates="atc_code", cascade="all, delete-orphan")
    alert_links: Mapped[list["AlertDrug"]] = relationship(back_populates="atc_code")
    study_links: Mapped[list["StudyDrug"]] = relationship(back_populates="atc_code")


class DrugATC(Base):
    __tablename__ = "drug_atc"
    __table_args__ = (UniqueConstraint("drug_id", "atc_code_id", name="uq_drug_atc"),)

    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"), primary_key=True)
    atc_code_id: Mapped[int] = mapped_column(ForeignKey("atc_codes.id"), primary_key=True)

    drug: Mapped[Drug] = relationship(back_populates="atc_links")
    atc_code: Mapped[ATCCode] = relationship(back_populates="drug_links")


class SafetyAlert(Base):
    __tablename__ = "safety_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    alert_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(80), nullable=True)

    source: Mapped[Source] = relationship(back_populates="alerts")
    drug_links: Mapped[list["AlertDrug"]] = relationship(back_populates="alert", cascade="all, delete-orphan")


class AlertDrug(Base):
    __tablename__ = "alert_drugs"
    __table_args__ = (UniqueConstraint("alert_id", "drug_id", "atc_code_id", name="uq_alert_drug_atc"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("safety_alerts.id"), nullable=False)
    drug_id: Mapped[int | None] = mapped_column(ForeignKey("drugs.id"), nullable=True)
    atc_code_id: Mapped[int | None] = mapped_column(ForeignKey("atc_codes.id"), nullable=True)

    alert: Mapped[SafetyAlert] = relationship(back_populates="drug_links")
    drug: Mapped[Drug | None] = relationship(back_populates="alert_links")
    atc_code: Mapped[ATCCode | None] = relationship(back_populates="alert_links")


class ConsumptionRecord(Base):
    __tablename__ = "consumption_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    geography: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    geography_type: Mapped[str] = mapped_column(String(80), nullable=False, default="country")
    population_group: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    atc_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    drug_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    active_ingredient: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    packages: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    ddd: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    dhd: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount_pvpiva: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[Source] = relationship(back_populates="consumption_records")


class StudyDocument(Base):
    __tablename__ = "study_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    geography: Mapped[str | None] = mapped_column(String(255), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusions: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_work: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    therapeutic_group: Mapped[str | None] = mapped_column(String(255), nullable=True)

    source: Mapped[Source | None] = relationship(back_populates="studies")
    drug_links: Mapped[list["StudyDrug"]] = relationship(back_populates="study", cascade="all, delete-orphan")


class StudyDrug(Base):
    __tablename__ = "study_drugs"
    __table_args__ = (UniqueConstraint("study_id", "drug_id", "atc_code_id", name="uq_study_drug_atc"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("study_documents.id"), nullable=False)
    drug_id: Mapped[int | None] = mapped_column(ForeignKey("drugs.id"), nullable=True)
    atc_code_id: Mapped[int | None] = mapped_column(ForeignKey("atc_codes.id"), nullable=True)

    study: Mapped[StudyDocument] = relationship(back_populates="drug_links")
    drug: Mapped[Drug | None] = relationship(back_populates="study_links")
    atc_code: Mapped[ATCCode | None] = relationship(back_populates="study_links")
