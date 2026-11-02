# LLM-Based Developmental Milestone Extraction Pipeline
### Toward the Automated Retrieval and Curation of Developmental Milestones Across Species

## Project Overview

Understanding developmental timelines across species requires the integration of observations scattered throughout a large and diverse scientific literature. Although developmental milestones have been reported in thousands of studies, retrieving, standardizing, and comparing these observations remains a largely manual and time-consuming process.

This project explores the use of **Large Language Models (LLMs) to automate the identification, retrieval, and structured extraction of developmental milestones from scientific literature**, initially focusing on mouse, rat, and human development.

The long-term goal is to develop a computational pipeline capable of systematically identifying developmental observations in scientific publications, extracting their associated ages and biological descriptions, and organizing them into a structured, traceable, and reusable database.

This repository documents the **initial stages of that effort**. The current implementation is a proof of concept designed to investigate whether LLM-based approaches can reproduce aspects of manual literature curation and facilitate the construction of comparative developmental datasets.

## Current Stage: Proof of Concept

The initial pipeline uses an existing manually curated dataset of developmental milestones as a reference resource for testing and validation.

The workflow currently explores the following steps:

1. **Literature retrieval:** identifying scientific publications through their DOIs and retrieving available abstracts and open-access full texts.
2. **Information extraction:** using LLMs to identify developmental observations and extract relevant information from abstracts and scientific articles.
3. **Data structuring:** converting extracted information into standardized, machine-readable records.
4. **Validation:** comparing LLM-extracted observations against manually curated reference data to assess extraction performance and identify limitations.

The current implementation includes experiments with both abstract-based and full-text extraction. These approaches represent initial steps toward a more comprehensive literature-mining framework.

Importantly, the reference dataset is not the intended endpoint of this project. It provides an initial benchmark against which automated extraction can be evaluated and improved.

## Reference Dataset

The current proof of concept uses a copy of an independently compiled and published dataset:

**Open Dataset of Developmental Timelines for Corresponding Milestones in Mice, Rats, and Humans**

- Zenodo: https://doi.org/10.5281/zenodo.23244347
- Species: Human, Mouse, and Rat.
- 783 developmental observations.
- 371 unique developmental milestones.
- Developmental periods: prenatal and postnatal.
- Domains: Body and Brain.

The dataset was assembled through systematic literature searches and manual curation, with observations traced back to their original empirical sources.

Within this project, it serves two complementary purposes:

- **Literature retrieval seed:** its DOI records provide an initial set of publications for testing automated literature retrieval.
- **Ground truth:** its manually curated observations provide a reference for evaluating the information extracted by LLMs.

The dataset is stored in the `data/` directory:

| File | Description |
| --- | --- |
| `dataset_mrh_0.9.csv` | Reference dataset containing 783 observations. |
| `DATA_DICTIONARY.md` | Description of variables, data types, and usage. |
| `README.md` | Information about the reference dataset. |
| `LICENSE` | License terms for the copied dataset (CC BY-NC-SA 4.0). |

**The original dataset is an independent research resource and is not a dataset produced by this LLM pipeline.** Please refer to its original Zenodo record and citation information below.

## Developmental Milestone Extraction

The pipeline aims to retrieve structured observations from scientific publications, including:

- Species.
- Developmental milestone or biological event.
- Developmental age.
- Age reference system and temporal units.
- Biological domain or tissue classification.
- Original publication and DOI.
- Supporting textual evidence or references to figures and tables.

An important aspect of the approach is **traceability**: extracted observations should remain linked to their original scientific sources, allowing subsequent verification and manual review.

Developmental ages may be reported using different temporal conventions, including gestational age, days after fertilization, postnatal days, weeks, or months. Their standardization is therefore an important component of the broader project.

## Repository Structure

The repository currently contains the following main components:

| Component | Purpose |
| --- | --- |
| `data/` | Reference dataset used for retrieval and validation. |
| `descargar_abstracts.py` | Stage 1: DOI-based abstract retrieval from PubMed. |
| `descargar_pdfs.py` | Stage 1 (alternative): open-access full-text PDF retrieval via OpenAlex. |
| `interpretar_abstracts2.py` | Stage 2: LLM-based (instructor/Pydantic) extraction from cached abstracts. |
| `DATA_EXTRACTOR_ABSTRACT.py` | Stage 2 (experimental alternative): LLM-based extraction directly from PDF text (Abstract + Results sections). |
| `compilar_csv.py` | Stage 3: compilation of extracted observations into a structured master CSV. |
| `requirements.txt` | Python dependencies for the pipeline. |
| `LICENSE` | License for the code in this repository. |

The codebase is experimental and will evolve as extraction strategies, validation procedures, and data structures are refined.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the repository root with:

```
GEMINI_API_KEY=your_gemini_api_key   # required, used by the extraction stages
NCBI_API_KEY=your_ncbi_api_key       # optional, raises the PubMed rate limit
```

## Future Directions

This proof of concept is the starting point of a broader research project aimed at developing increasingly automated approaches to developmental literature curation.

Potential future developments include:

- Expanding literature retrieval beyond the initial reference publications.
- Improving the extraction of developmental ages and milestone descriptions from full-text articles.
- Identifying and resolving duplicate observations across publications.
- Standardizing milestone terminology across species.
- Extracting supporting evidence from tables, figures, and supplementary materials.
- Developing systematic methods to assess extraction accuracy and reliability.
- Integrating newly retrieved observations into an expanding, traceable developmental milestone database.

Ultimately, the goal is to move toward a **semi-automated and continuously expandable resource for developmental biology and comparative neuroscience**, reducing the effort required to identify, curate, and integrate developmental information from the scientific literature.

## How to Cite the Reference Dataset

The dataset included in this repository was originally compiled and published independently of the LLM extraction project.

If you use the reference dataset, including through this pipeline, please cite:

Amici E, Grimson R, Vazquez-Borsetti P. Open Dataset of Developmental Timelines for Corresponding Milestones in Mice, Rats, and Humans. (Manuscript in preparation, 2026).

Amici E, Grimson R, Vazquez-Borsetti P. Open Dataset of Developmental Timelines for Corresponding Milestones in Mice, Rats, and Humans [Data set]. Zenodo, 2026. https://doi.org/10.5281/zenodo.23244347

## Related Work

The reference dataset expands a previously published rat-human developmental resource:

Campos Eusebi W, Iorii T, et al. Divergent Pattern of Development in Rats and Humans. *Neurotoxicity Research*. 2024. https://doi.org/10.1007/s12640-023-00683-y

Companion dataset: https://github.com/Vazquez-Borsetti/rat-and-human-comparative-development

The comparative developmental modeling framework associated with this research is described in a companion project:

https://github.com/Vazquez-Borsetti/quarter-power-C-human-rodent-translation

## Author

**Pablo Vazquez-Borsetti**

Instituto de Biología Celular y Neurociencia (IBCN), Universidad de Buenos Aires (UBA) and Consejo Nacional de Investigaciones Científicas y Técnicas (CONICET), Argentina.

## License

The code in this repository (all `.py` scripts) is distributed under the **MIT License**.
See `LICENSE` for the applicable terms.

The reference dataset included in `data/` is distributed separately under the Creative
Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0).
See `data/LICENSE` for the applicable terms.

## Acknowledgments

This project builds upon the work of researchers whose studies have contributed to the scientific understanding of developmental processes across species.

We acknowledge the original authors of the studies included in the reference dataset and the contributors involved in its compilation and manual curation.