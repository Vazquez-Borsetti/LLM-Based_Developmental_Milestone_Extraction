# Reference Dataset (`data/`)

This folder contains a copy of an independently published dataset of developmental milestones
in mouse, rat, and human, used in this repository as the **seed/ground-truth data** for the
LLM-based extraction pipeline. See the repository-level [README](../README.md) for how this
dataset fits into the overall project.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23244347.svg)](https://doi.org/10.5281/zenodo.23244347)

## Files

| File | Description |
| --- | --- |
| `dataset_mrh_0.9.csv` | The curated dataset: 783 rows x 11 columns, one row per (Species, Parameter, Reference) age record. |
| `DATA_DICTIONARY.md` | Detailed column-by-column data dictionary, including types, cardinality, and usage notes. |
| `README.md` | This file. |
| `LICENSE` | License terms for this dataset (CC BY-NC-SA 4.0). |

## Dataset Columns

| Column | Description |
| --- | --- |
| `Species` | Species of the observation: `Human`, `Mouse`, or `Rat`. |
| `Parameter` | Name/description of the developmental milestone, standardized across sources to avoid duplicate naming of the same event. |
| `DAF` | **Days After Fertilization** — standardized developmental age, with fertilization defined as day 0. Primary age variable used throughout the analyses. |
| `Reference` | Bibliographic citation (author, year) for the source of the record. |
| `Obs` | Free-text curator notes (e.g., justification for excluding/adjusting a value, discrepancies with the cited source, data-quality caveats). |
| `Quote` | Traceability field: verbatim excerpt from the source text and/or reference to a supporting figure/table. |
| `DOI` | Digital Object Identifier of the reference, used as a unique key for reference-level aggregation. |
| `link` | Alternative URL to the source when no DOI is available (e.g., scanned books). |
| `Cluster` | Tissue/domain classification of the milestone: `Brain` or `Body`. Missing only for the `Birth` reference rows. |
| `Data_curator` | Name of the person/team who curated the record (used for provenance). |
| `GA(H+14)` | Human **Gestational Age**, counted from the last menstrual period (LMP), computed as `DAF + 14`. Only populated for `Species == Human`. |

See `DATA_DICTIONARY.md` for full details, including cardinality and missing-data counts per
column.

## How to Cite

This dataset was originally compiled and published independently of the LLM extraction
project in this repository. If you use it (including through this pipeline), please cite:

> Amici E, Grimson R, Vazquez-Borsetti P. Open Dataset of Developmental Timelines for
> Corresponding Milestones in Mice, Rats, and Humans. (manuscript in preparation, 2026).

> Amici E, Grimson R, Vazquez-Borsetti P. Open Dataset of Developmental Timelines for
> Corresponding Milestones in Mice, Rats, and Humans [Data set]. Zenodo, 2026.
> https://doi.org/10.5281/zenodo.23244347

## License

This dataset is released under the **Creative Commons Attribution-NonCommercial-ShareAlike
4.0 International License (CC BY-NC-SA 4.0)**. See `LICENSE` in this folder for the full
terms. This is independent of the MIT license covering the pipeline code (see the repository
root `LICENSE`).
