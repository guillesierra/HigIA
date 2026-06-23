# Source Inventory

This file records initial public sources considered by HigIA. Every ingested record should keep URL, access date, extraction method, and license or redistribution notes when known.

## AEMPS

- Name: AEMPS medicine safety notes.
- URL: https://www.aemps.gob.es/comunicacion/notas-de-seguridad/notas-informativas-de-seguridad-de-medicamentos-de-uso-humano/
- Expected data: publication date, title, organization, note code, alert category, link, summary, and full text when available.
- Notes: use only public pages and downloadable public files. Preserve source URL and raw HTML/PDF.

## Ministry Of Health Spain

- Name: Medicine consumption charged to the SNS by ATC.
- Methodology/public note: https://www.sanidad.gob.es/gabinete/notasPrensa.do?id=5655
- Interactive statistical note: https://pestadistico.inteligenciadegestion.sanidad.gob.es/publicoSNS/D/consumo-farmaceutico-en-el-sns/consumo-en-recetas-medicas-sns/consumo-medicamentos-por-atc/nota-metodologica
- Expected data: year, ATC level/code/name, packages, DHD, PVPIVA amount, national scope, and method notes.
- Notes: interactive portals may need manual export or a source-specific connector if no static tabular link is exposed.

## PRAN

- Name: Human antibiotic consumption maps.
- URL: https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumos-antibioticos-humana
- Community scope: https://www.resistenciaantibioticos.es/es/lineas-de-accion/vigilancia/mapas-de-consumo/consumo-antibioticos-humana/consumos-antibioticos-extrahospitalarios-por-comunidades
- Expected data: year, scope, community, sector, antibiotic category or ATC, DHD, and source page/document.
- Notes: the first scraper discovers downloadable links and documents; structured extraction can be hardened once the exact public export format is confirmed.

## Asturias

- Name: Astursalud, SESPA, OETSPA, and related public documents.
- Candidate domains: `astursalud.es`, `sespa.es`, `oetspa.astursalud.es`, `huca.sespa.es`.
- Expected data: public PDFs and pages about PROA, antibiotics, benzodiazepines, psychopharmaceuticals, pharmacovigilance, pharmacy, and rational medicine use.
- Notes: the Asturias scraper catalogs public documents and extracts metadata/text when reliable. It should never infer structured consumption metrics from ambiguous PDF text.

## WHO ATC/DDD

- Name: WHO Collaborating Centre ATC/DDD Index.
- URL: https://atcddd.fhi.no/atc_ddd_index/
- Expected data: ATC code, name, level, DDD when terms allow.
- Notes: consult and respect terms of use before redistribution.

