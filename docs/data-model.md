# Data Model

HigIA stores normalized public data in SQLite for the MVP, using SQLAlchemy models designed to migrate to PostgreSQL.

## Core Entities

- `Source`: public data source, URL, source type, license/status, access date, and notes.
- `Drug`: medicine or active ingredient name with normalized fields.
- `ATCCode`: ATC code hierarchy.
- `DrugATC`: many-to-many link between drugs and ATC codes.
- `SafetyAlert`: AEMPS or related alert/note with date, title, URL, summary, raw text, and organization.
- `AlertDrug`: link between alerts, drugs, and ATC codes.
- `ConsumptionRecord`: aggregated consumption metric by year/month, geography, ATC, drug, active ingredient, packages, DDD, DHD, amount, and unit.
- `StudyDocument`: public technical/scientific document metadata and extracted summary.
- `StudyDrug`: link between study documents, drugs, and ATC codes.

## Provenance Rules

- Every alert, consumption row, or document should point to a `Source`.
- Every raw download should be stored under `data/raw/<source>`.
- Every processed public export should be reproducible from SQLite or documented manual steps.
- Ambiguous extraction is allowed as notes, not as authoritative structured data.

