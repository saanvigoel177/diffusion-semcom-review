# Diffusion models for noise mitigation in semantic communication: search, screening and extraction record

Data and scripts for the review "Diffusion Models for Channel and Adversarial Noise Mitigation in Wireless Semantic Communication: A Review" by Saanvi Goel and Syamasudha Veeragandham (Vellore Institute of Technology), submitted to *Artificial Intelligence Review*. This repository is Online Resource 1 of the article.

It documents how 151 studies were found, screened and characterized, and it reproduces the counts in Table 2 and Figs. 1 and 4 of the article.

## Contents

| Path | What it holds |
|---|---|
| `data/raw/` | Search exports as retrieved in October 2026: IEEE Xplore (280), arXiv (127), OpenAlex (334), citation chasing from four seed papers (175), the 242 new records of the broader OpenAlex search (`supplementary_openalex_new_records.json`) and the Semantic Scholar records (`semanticscholar_records.txt`). |
| `data/screening.csv` | All 719 records after de-duplication, with the title and abstract decision, the full-text decision (include, exclude, discussed), the reason, the basis of assessment (full text or abstract), the category and an eligibility note. Ids 455 to 696 come from the broader OpenAlex search and ids 697 to 719 from Semantic Scholar. |
| `data/included_studies.csv` | The 151 included studies with subcategory (3a to 7c, as in Table 3 of the article), year, modality, channels evaluated, core mechanism, basis of assessment, DOI, arXiv id and full reference. |
| `data/abstract_level_extraction.csv` | Fields extracted for every record included at title and abstract screening. |
| `data/fulltext_extraction_priority.csv`, `data/fulltext_extraction_notes.md` | Full-text extraction, with section and table pointers into each paper. |
| `data/maybes_resolved.csv` | Records first marked "maybe" at title and abstract screening, with the decision and reason. |
| `data/second_assessment/` | The blind second assessment of a stratified random sample of 50 records (seed 20261017; 30 of the 168 assessed for eligibility and 20 of the 551 excluded at screening), made from titles and abstracts only. `blind_sample.csv` lists the records, `blind_decisions.csv` the second decisions and `blind_key.json` maps each sample id to its record id and original decision. |
| `scripts/` | `fetch_sources.py` (queries and retrieval), `search_log.py` (merge, screening helpers and the Table 2 tally), `make_fig_trend.py` (Fig. 1) and `make_fig_start_index.py` (Table 5 and Fig. 4). |
| `figures/` | The two figures produced by the scripts, as used in the article. |

**Abstracts are not included.** The exports and the screening table were made with abstracts, but abstract text is removed here because publishers restrict its redistribution. Every record keeps its title, year, DOI or arXiv id, so the abstracts can be retrieved from the original sources. The second assessor saw titles and abstracts; `blind_key.json` links each sample record to `data/screening.csv`, which holds its DOI.

## Eligibility rule

A study is included if (a) a diffusion, score-based, flow-matching or bridge generative model is part of the receiver or of a defense, (b) its output depends on evidence that has passed through a noisy wireless channel, and (c) reconstruction or task quality is evaluated over at least one noisy channel setting. Conference and journal versions, and preprint and published versions, of one study are counted once. Theses and coursework reports are excluded as grey literature.

## Reproducing the counts

Python 3 with `numpy` (and `matplotlib` for the figures).

```bash
cd data && python ../scripts/search_log.py tally
```

prints the flow of records in Table 2: 719 after de-duplication, 551 excluded at title and abstract, 168 assessed for eligibility, 17 excluded or discussed (2 discussed), 151 included.

```bash
cd figures && python ../scripts/make_fig_start_index.py
```

prints the start indices of Table 5, stops with an error if they differ from the table, and draws Fig. 4.

```bash
cd figures && python ../scripts/make_fig_trend.py
```

draws Fig. 1.

The blind second assessment agrees with the original decisions on 46 of 50 records (Cohen's kappa 0.84), on 27 of the 30 eligibility records (kappa 0.52) and on 19 of the 20 screening exclusions.

## Notes on specific records

Seven studies first characterized from their abstracts were re-assessed on the full text (ids 11, 18, 76, 79, 109, 272, 274). Record 307 has no reachable abstract or full text and keeps its title and abstract exclusion. Record 699 (DENOISE) has no abstract or open full text and is excluded at eligibility as not assessable.

## Licence

The data in `data/` and `figures/` are released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0). The scripts in `scripts/` are released under the MIT licence (see `LICENSE`).

## Citation

If you use this record, please cite the article: Goel S, Veeragandham S. Diffusion models for channel and adversarial noise mitigation in wireless semantic communication: A review. Submitted to *Artificial Intelligence Review* (2026).
