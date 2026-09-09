# IndustrialReliability dataset

Generated: 2026-09-07T10:07:29+00:00

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

- Records: **386** (arxiv (197), openalex (189))
- Train / Test: **308 / 78**
- With PDF: **193** (50% coverage)

## Records by sub-area (train / test)

| Sub-area | Total | Train | Test |
|---|--:|--:|--:|
| AnomalyDetection | 50 | 40 | 10 |
| BearingFaultDiagnosis | 48 | 38 | 10 |
| DigitalTwin | 49 | 39 | 10 |
| PredictiveMaintenance | 49 | 39 | 10 |
| ProcessMonitoring | 45 | 36 | 9 |
| QualityInspection | 49 | 39 | 10 |
| RemainingUsefulLife | 50 | 40 | 10 |
| VibrationAnalysis | 46 | 37 | 9 |

Each record matches `bridgescout.ingestion.preprocessing.Paper` (`limitations_text` / `method_text` mirror the abstract), plus `sub_area`, `url`, `doi`, `pdf_path`, `pdf_source`, `split`.
