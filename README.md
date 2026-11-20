# UAS Airflow — Online Retail II

Starter repository for Kelompok 4's ETL pipeline and Airflow monitoring/error-handling project.

> **Scaffold only.** This archive contains directory structure and starter placeholders, **not** a runnable Airflow pipeline. `docker-compose.yml` has no configured services yet.

## Proposed workflow
1. **Anggota 1:** Obtain Online Retail II dataset, document the source and create `src/extract.py`.
2. **Ketua / Anggota 2:** Implement validation and transformations in `src/validate_transform.py`.
3. **Anggota 3:** Define PostgreSQL schema in `sql/` and loading code in `src/load.py`.
4. **Anggota 4 (+ Ketua support):** Implement Airflow DAG in `dags/`, Docker Compose services, task dependency, logging, retry and failure tests.
5. **Anggota 5:** Collect evidence and write the report under `docs/report/`.
6. **Anggota 6:** Develop presentation and demo under `docs/showcase/`.

## Git collaboration
- `main`: stable/final version.
- `develop`: integration branch.
- Each member creates a working branch from `develop`, tests locally, pushes, and opens a PR into `develop`.
- The Ketua reviews handoff output, test evidence and PR before merging.
- Merge `develop` into `main` only after end-to-end tests and documentation review.

## Data management
`data/raw/` and `data/processed/` are Git-ignored except for `.gitkeep`. Add source/download instructions in this README or create a dedicated downloader when implementing Extract. Avoid committing credentials or oversized datasets.

## Documentation evidence
Each technical owner should provide essential output/test evidence, not screenshots of every trivial coding step. Report and showcase owners curate those results.
