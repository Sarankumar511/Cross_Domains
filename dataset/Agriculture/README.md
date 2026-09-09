# Agriculture dataset

Generated: 2026-09-07T09:58:52+00:00

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

- Records: **367** (arxiv (181), openalex (186))
- Train / Test: **293 / 74**
- With PDF: **177** (48% coverage)

## Records by sub-area (train / test)

| Sub-area | Total | Train | Test |
|---|--:|--:|--:|
| CropDiseaseDetection | 50 | 40 | 10 |
| FewShotAugmentation | 46 | 37 | 9 |
| LivestockMonitoring | 48 | 38 | 10 |
| PlantPhenotyping | 46 | 37 | 9 |
| PrecisionAgriculture | 33 | 26 | 7 |
| SoilMonitoring | 49 | 39 | 10 |
| WeedPestDetection | 47 | 38 | 9 |
| YieldPrediction | 48 | 38 | 10 |

Each record matches `bridgescout.ingestion.preprocessing.Paper` (`limitations_text` / `method_text` mirror the abstract), plus `sub_area`, `url`, `doi`, `pdf_path`, `pdf_source`, `split`.
