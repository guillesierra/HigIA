# Roadmap

## MVP

- Scaffold backend, frontend, scripts, and docs.
- Keep runtime data real-only: empty schema by default, then populate from public-source scrapers.
- Implement conservative scrapers that discover and store public links/documents.
- Export public JSON for GitHub Pages.
- Display sources, alerts, consumption charts, relations, Asturias documentation, and methodology.

## Next

- Add source-specific parsers for confirmed public CSV/XLS/XLSX exports.
- Add validation reports for every scrape and normalization run.
- Add stronger ATC and active ingredient matching.
- Add duplicate detection for alerts and documents.
- Add richer time-series analysis around safety alerts.

## Later

- Add PostgreSQL support.
- Deploy backend to Render, Fly.io, Railway, or a VPS.
- Add scheduled GitHub Actions for public-source refreshes if source terms permit it.
- Add OpenAPI client generation for the frontend.
