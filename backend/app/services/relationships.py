from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.domain import ATCCode, AlertDrug, ConsumptionRecord, Drug, DrugATC, SafetyAlert, Source, StudyDocument, StudyDrug
from app.normalizers.text import normalize_name
from app.schemas.domain import RelationshipResponse


def relationship_for_drug(db: Session, query: str) -> RelationshipResponse:
    normalized = normalize_name(query)
    drugs = db.scalars(
        select(Drug).where(
            or_(
                Drug.normalized_name.ilike(f"%{normalized}%"),
                Drug.active_ingredient.ilike(f"%{query}%"),
                Drug.name.ilike(f"%{query}%"),
            )
        )
    ).all()
    drug_ids = [drug.id for drug in drugs]

    atc_codes = []
    alerts = []
    studies = []
    if drug_ids:
        atc_codes = db.scalars(
            select(ATCCode)
            .join(DrugATC)
            .where(DrugATC.drug_id.in_(drug_ids))
            .distinct()
        ).all()
        alerts = db.scalars(
            select(SafetyAlert)
            .join(AlertDrug)
            .where(AlertDrug.drug_id.in_(drug_ids))
            .distinct()
        ).all()
        studies = db.scalars(
            select(StudyDocument)
            .join(StudyDrug)
            .where(StudyDrug.drug_id.in_(drug_ids))
            .distinct()
        ).all()

    consumption = db.scalars(
        select(ConsumptionRecord)
        .where(
            or_(
                ConsumptionRecord.drug_name.ilike(f"%{query}%"),
                ConsumptionRecord.active_ingredient.ilike(f"%{query}%"),
            )
        )
        .order_by(ConsumptionRecord.year)
        .limit(250)
    ).all()

    sources = _sources_for_records(db, alerts, consumption, studies)
    return RelationshipResponse(
        query=query,
        drugs=list(drugs),
        atc_codes=list(atc_codes),
        alerts=list(alerts),
        consumption=list(consumption),
        studies=list(studies),
        sources=sources,
    )


def relationship_for_atc(db: Session, code: str) -> RelationshipResponse:
    atc_codes = db.scalars(select(ATCCode).where(ATCCode.code.ilike(f"{code}%"))).all()
    atc_ids = [item.id for item in atc_codes]
    drugs = []
    alerts = []
    studies = []
    if atc_ids:
        drugs = db.scalars(select(Drug).join(DrugATC).where(DrugATC.atc_code_id.in_(atc_ids)).distinct()).all()
        alerts = db.scalars(select(SafetyAlert).join(AlertDrug).where(AlertDrug.atc_code_id.in_(atc_ids)).distinct()).all()
        studies = db.scalars(select(StudyDocument).join(StudyDrug).where(StudyDrug.atc_code_id.in_(atc_ids)).distinct()).all()

    consumption = db.scalars(
        select(ConsumptionRecord)
        .where(ConsumptionRecord.atc_code.ilike(f"{code}%"))
        .order_by(ConsumptionRecord.year)
        .limit(250)
    ).all()

    sources = _sources_for_records(db, alerts, consumption, studies)
    return RelationshipResponse(
        query=code,
        drugs=list(drugs),
        atc_codes=list(atc_codes),
        alerts=list(alerts),
        consumption=list(consumption),
        studies=list(studies),
        sources=sources,
    )


def relationship_for_alert(db: Session, alert_id: int) -> RelationshipResponse:
    alert = db.get(SafetyAlert, alert_id)
    if alert is None:
        raise ValueError("Alert not found")

    links = db.scalars(select(AlertDrug).where(AlertDrug.alert_id == alert_id)).all()
    drug_ids = [link.drug_id for link in links if link.drug_id]
    atc_ids = [link.atc_code_id for link in links if link.atc_code_id]
    drugs = db.scalars(select(Drug).where(Drug.id.in_(drug_ids))).all() if drug_ids else []
    atc_codes = db.scalars(select(ATCCode).where(ATCCode.id.in_(atc_ids))).all() if atc_ids else []
    atc_prefixes = [item.code for item in atc_codes]

    consumption_stmt = select(ConsumptionRecord).order_by(ConsumptionRecord.year).limit(250)
    if atc_prefixes:
        filters = [ConsumptionRecord.atc_code.ilike(f"{code}%") for code in atc_prefixes]
        consumption_stmt = consumption_stmt.where(or_(*filters))
    elif drugs:
        filters = [ConsumptionRecord.drug_name.ilike(f"%{drug.name}%") for drug in drugs]
        consumption_stmt = consumption_stmt.where(or_(*filters))
    consumption = db.scalars(consumption_stmt).all()

    studies = []
    if drug_ids or atc_ids:
        clauses = []
        if drug_ids:
            clauses.append(StudyDrug.drug_id.in_(drug_ids))
        if atc_ids:
            clauses.append(StudyDrug.atc_code_id.in_(atc_ids))
        studies = db.scalars(select(StudyDocument).join(StudyDrug).where(or_(*clauses)).distinct()).all()

    sources = _sources_for_records(db, [alert], consumption, studies)
    return RelationshipResponse(
        query=str(alert_id),
        drugs=list(drugs),
        atc_codes=list(atc_codes),
        alerts=[alert],
        consumption=list(consumption),
        studies=list(studies),
        sources=sources,
    )


def _sources_for_records(
    db: Session,
    alerts: list[SafetyAlert],
    consumption: list[ConsumptionRecord],
    studies: list[StudyDocument],
) -> list[Source]:
    source_ids = {item.source_id for item in alerts if item.source_id}
    source_ids.update(item.source_id for item in consumption if item.source_id)
    source_ids.update(item.source_id for item in studies if item.source_id)
    if not source_ids:
        return []
    return list(db.scalars(select(Source).where(Source.id.in_(source_ids))).all())

