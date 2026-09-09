# EarthEnvironment dataset

Generated: 2026-09-07T09:45:39+00:00

Real research papers from **arxiv, openalex**, spanning 8 sub-areas, with a reproducible stratified 80/20 train/test split (seed 42).

## Contents

| File | What |
|---|---|
| `all_papers.json` | Every de-duplicated record |
| `train.json` / `test.json` | The split, stratified by sub-area |
| `split_manifest.json` | Counts, parameters, seed, PDF coverage |
| `pdfs/<id>.pdf` | Open-access full text where reachable |
| `raw/raw.json` | Unprocessed fetch output |

## Totals

- Records: **375** (arxiv (178), openalex (197))
- Train / Test: **300 / 75**
- With PDF: **171** (46% coverage)

## Records by sub-area (train / test)

| Sub-area | Total | Train | Test |
|---|--:|--:|--:|
| AirQuality | 48 | 38 | 10 |
| ClimateModeling | 50 | 40 | 10 |
| GeospatialMapping | 47 | 38 | 9 |
| Hydrology | 50 | 40 | 10 |
| NaturalHazards | 44 | 35 | 9 |
| Oceanography | 37 | 30 | 7 |
| RemoteSensing | 50 | 40 | 10 |
| Seismology | 49 | 39 | 10 |

Each record matches `bridgescout.ingestion.preprocessing.Paper` (`limitations_text` / `method_text` mirror the abstract), plus `sub_area`, `url`, `doi`, `pdf_path`, `pdf_source`, `split`.
