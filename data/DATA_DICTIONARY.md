# Data Dictionary — `dataset_mrh_0.9.csv`

Comparative dataset of developmental milestones in Mouse, Rat and Human, compiled from a
systematic literature review. Each row is one reported observation of a developmental
milestone (age at which it occurs) for a given species, extracted from a single source.

- **Rows:** 783
- **Columns:** 11
- **Unit of observation:** one (Species, Parameter, Reference) age record
- **Unique developmental milestones (`Parameter`):** 371
- **Unique references:** 397

## Columns

| Column | Type | Unique values | Description |
|---|---|---|---|
| `Species` | string (categorical) | 3 | Species the observation belongs to. Values: `Human` (377), `Mouse` (206), `Rat` (200). |
| `Parameter` | string (categorical) | 371 | Name/description of the developmental milestone (e.g. "GE volume peak", "Birth", "Eye opening"). Curated/standardized across sources to avoid duplicate naming of the same event. |
| `DAF` | float | 216 | **Days After Fertilization** — Standardized age at which the milestone occurs, with fertilization defined as day 0. This is the primary age variable used throughout the analysis. When multiple sources report different ages for the same Species+Parameter, records are kept separately (not averaged in the raw file) — the mean is computed downstream as the representative value. |
| `Reference` | string | 397 | Bibliographic citation (author, year) for the source of the record. |
| `Obs` | string | 108 | Free-text curator notes, e.g. justification for excluding/adjusting a value, discrepancies with the cited source, or data-quality caveats. Populated only when a note was needed (missing in 620 rows). |
| `Quote` | string | 413 | Traceability field: verbatim excerpt from the source text (and/or a reference to a supporting figure/table) supporting the reported value. |
| `DOI` | string | 372 | Digital Object Identifier of the reference, used as a unique key for reference-level aggregation (e.g. counting records per source). Missing for a few older/non-indexed sources (3 rows; see `Obs`/`link` for alternate access). |
| `link` | string | 22 | Alternative URL to the source when no DOI is available (e.g. HathiTrust book scans). Only populated for non-DOI sources (missing in 693 rows). |
| `Cluster` | string (categorical) | 2 | Tissue/domain classification of the milestone: `Brain` (307) or `Body` (472). Missing only for the 4 `Birth` reference rows (used to anchor per-species birth date. |
| `Data_curator` | string (categorical) | 7 | Name of the person/team who curated the record: `Otis 1954`, `Ohmura 2017`, `Campos-Iorii 2023`, `Amici`, `Cottam 2024`, `Godlewski 1997`, `Clancy 2001`. Used for provenance and to audit curation batches. |
| `GA(H+14)` | float | 47 | Human **Gestational Age** counted from the last menstrual period (LMP), computed as `DAF + 14` (14 days is the assumed interval between LMP and fertilization). Only meaningful/populated for `Species == Human`; provided as a convenience for reporting ages in the clinically conventional GA scale alongside DAF (populated in only 58 rows total). |

## Notes on derived/downstream usage

- `Birth` is a special `Parameter` value (one row per species) used to look up each species'
  birth DAF (`get_birth_values()` in `src/config.py`); it has no `Cluster`.
- Analyses pivot the table by `Parameter` × `Species` (mean `DAF`) to compare milestone timing
  across species, and group by `DOI`/`Reference` to summarize source contributions.
- Duplicate `Parameter` + `Species` combinations are expected (multiple sources reporting the
  same milestone) and are resolved by averaging `DAF` downstream, not in this raw file.
