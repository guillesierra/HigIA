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

## Spanish Universities

- Name: University of Oviedo RUO / DIGIBUO record.
- URL: https://digibuo.uniovi.es/dspace/handle/10651/45002
- Expected data: thesis/publication metadata, public PDF links when available, title, authors, year, abstract or extracted text, DOI if present, geography, and therapeutic group inferred from text.
- Notes: this URL may deny automated access depending on robots or server policy. The scraper records the error and continues.

- Name: University of Oviedo Research Portal article record.
- URL: https://portalinvestigacion.uniovi.es/documentos/667c517a6de8e7265d987072?lang=en
- Expected data: title, authors, journal, year, pages, DOI, external full text link, abstract, Asturias-related antibiotic consumption metadata.
- Notes: this is a high-priority source for the publication "Evolucion del consumo de antibioticos a nivel extrahospitalario en Asturias, Espana (2005-2018)".

- Name: Additional Spanish university repositories.
- Generic UniOvi seed URLs:
  - https://digibuo.uniovi.es/dspace/
  - https://digibuo.uniovi.es/dspace/simple-search?query=antibioticos
  - https://digibuo.uniovi.es/dspace/simple-search?query=medicamentos
  - https://digibuo.uniovi.es/dspace/simple-search?query=farmacia
  - https://digibuo.uniovi.es/dspace/simple-search?query=consumo%20antibioticos
  - https://digibuo.uniovi.es/dspace/simple-search?query=DDD
  - https://digibuo.uniovi.es/dspace/simple-search?query=DHD
  - https://portalinvestigacion.uniovi.es/
  - https://portalinvestigacion.uniovi.es/resultados/publicaciones
  - https://portalinvestigacion.uniovi.es/resultados/tesis/anualidades
- High-signal UniOvi seed URLs:
  - https://digibuo.uniovi.es/dspace/handle/10651/45002
  - https://portalinvestigacion.uniovi.es/documentos/667c517a6de8e7265d987072?lang=en
  - https://digibuo.uniovi.es/dspace/handle/10651/16740
  - https://digibuo.uniovi.es/dspace/bitstream/10651/34879/1/TD_CristinaMariaSuarezCastanon.pdf
  - https://digibuo.uniovi.es/dspace/bitstream/handle/10651/50389/TD_DiegoParraRuiz.pdf
  - https://digibuo.uniovi.es/dspace/bitstream/handle/10651/13462/TD_pedrojavierguerrero.pdf?isAllowed=y&sequence=2
  - https://digibuo.uniovi.es/dspace/bitstream/handle/10651/72580/2024_025_TD_PilarLumbrerasIglesias.pdf?isAllowed=y&sequence=1
- Other Spanish university seed URLs:
  - https://eprints.ucm.es/51527/
  - https://repositorio.uam.es/
  - https://idus.us.es/
  - https://riunet.upv.es/
  - https://digitum.um.es/
  - https://e-spacio.uned.es/
  - https://zaguan.unizar.es/
  - https://diposit.ub.edu/
- Expected data: public academic documents about medicines, pharmacy, antibiotic consumption, antimicrobial resistance, ATC/DDD/DHD, rational medicine use, pharmacovigilance, benzodiazepines, and psychopharmaceuticals.
- Notes: use only public pages and PDFs, respect `robots.txt`, apply delays, store raw files, and treat extracted text as document metadata unless a structured table is explicitly available.

## WHO ATC/DDD

- Name: WHO Collaborating Centre ATC/DDD Index.
- URL: https://atcddd.fhi.no/atc_ddd_index/
- Expected data: ATC code, name, level, DDD when terms allow.
- Notes: consult and respect terms of use before redistribution.
