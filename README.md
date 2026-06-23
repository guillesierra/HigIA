# HigIA

HigIA is a personal research/software project for collecting, normalizing, linking, and visualizing public information about medicines, safety alerts, ATC/DDD classification, pharmacotherapeutic documents, and medicine consumption in Asturias and Spain.

The project is designed as an evolvable platform, not as a one-off script. It only handles public, aggregated, non-identifiable information.

## Scope

- Public AEMPS medicine safety notes and related alerts.
- Public Ministry of Health medicine consumption information for the Spanish National Health System.
- Public PRAN antibiotic consumption pages and documents.
- Public Astursalud, SESPA, OETSPA, and related Asturias documents.
- Open Access scientific or technical documents relevant to medicine consumption in Asturias or Spain.

## Architecture

- `backend`: FastAPI API, SQLite storage, SQLAlchemy models, Pydantic schemas, scrapers, normalizers, and tests.
- `frontend`: React + Vite static web app with API mode and JSON fallback mode.
- `data`: raw downloads, processed files, metadata, and public JSON exports.
- `docs`: source inventory, data model, legal notes, and roadmap.
- `scripts`: command-line entry points for scraping, normalization, seeding, and static export.

## Quick Start

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ..\scripts\seed_db.py
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

`seed_db.py` only creates the database schema. It does not insert demo records; publishable data should come from scrapers or reviewed public documents.

To remove legacy demo rows from an existing local SQLite database:

```powershell
python ..\scripts\purge_demo_data.py
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend will be available at the URL printed by Vite.

### Run Scrapers

```powershell
python scripts\run_scrapers.py --source all --limit 10 --persist
```

Scrapers are intentionally conservative. They check `robots.txt` for HTTP sources, use an identifiable `User-Agent`, apply a delay between requests, save raw HTML/PDF/CSV/XLS/XLSX, write source metadata and JSONL fetch/error logs, and export normalized JSON under `data/processed/<source>`.

Each scraper can run independently:

```powershell
python scripts\run_scrapers.py --source aemps --limit 20
python scripts\run_scrapers.py --source sanidad --limit 20
python scripts\run_scrapers.py --source pran --limit 20
python scripts\run_scrapers.py --source asturias --limit 20
python scripts\run_scrapers.py --source universities --limit 20
python scripts\run_scrapers.py --source manual --limit 20
```

If Windows, a corporate network, or a public repository with a misconfigured certificate returns
`CERTIFICATE_VERIFY_FAILED`, keep the normal mode as the default and rerun only when needed with:

```powershell
python scripts\run_scrapers.py --source universities --limit 50 --persist --timeout 8 --allow-insecure-ssl
```

The insecure SSL flag is explicit because it disables certificate verification for scraping requests.
It still checks `robots.txt`, keeps the project `User-Agent`, saves raw data, and logs source errors.
When SSL validation is enabled and a host fails certificate verification, the scraper records the
error once and skips later URLs from that same origin quickly.

If a public source changes, the run records an error row and continues with other records/sources. Scrapers do not invent unavailable fields; pages or PDFs without structured data are stored as documents with basic metadata and pending-review notes.

### Normalize Data

```powershell
python scripts\normalize_data.py
```

### Export Static JSON

```powershell
python scripts\export_public_json.py --frontend-public
```

This exports selected public, processed data from SQLite to `data/processed/public` and optionally copies it to `frontend/public/data` for GitHub Pages.

## GitHub Pages

The frontend can be deployed as a static site. In that mode, the app first tries the FastAPI API and then falls back to JSON files under `data/*.json`.

```powershell
python scripts\export_public_json.py --frontend-public
cd frontend
npm run build
```

An optional GitHub Actions workflow is included at `.github/workflows/deploy-pages.yml`.

## Data And Legal Notes

- No personal data or identifiable health data should be scraped, stored, or published.
- Each source record stores URL, access date, known license/status, and acquisition method notes.
- Data redistribution depends on the original source license and terms of use.
- Raw downloaded files should be reviewed before publishing.
- Static JSON export is intended for public, aggregated, non-sensitive data only.

## MVP Status

This repository includes:

- SQLAlchemy data model for sources, drugs, ATC codes, alerts, consumption records, studies, and relationships.
- FastAPI endpoints for listing and filtering the main entities.
- Basic before/after alert comparison endpoint.
- Initial scrapers and document ingesters with extensible interfaces.
- Normalizers for text, alert records, consumption dataframes, and PDFs.
- React pages for sources, alerts, consumption, relations, Asturias, and methodology.
- ECharts visualizations.
- Empty-by-default database initialization; runtime data is populated only from public-source scrapers or reviewed imports.
- Basic backend tests.

## Limitations

- Some official pages are interactive and may not expose direct CSV/XLS links through static HTML.
- PDF extraction quality varies; uncertain extraction is stored as metadata rather than as authoritative structured data.
- Asturias-specific public consumption datasets may be sparse; the model supports Spain and autonomous community data when available.
- Internal SESPA datasets are out of scope unless explicitly obtained and publishable under valid permissions.

## Roadmap

1. Harden each official-source scraper and document parser.
2. Add source-specific validation reports.
3. Improve ATC and active ingredient entity resolution.
4. Add richer before/after statistical methods.
5. Add provenance pages for every exported dataset.
6. Prepare PostgreSQL migration and hosted backend deployment.
