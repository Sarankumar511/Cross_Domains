# SignalProcessing dataset

Generated: 2026-09-07T09:21:08+00:00

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

- Records: **390** (arxiv (194), openalex (196))
- Train / Test: **311 / 79**
- With PDF: **190** (49% coverage)

## Records by sub-area (train / test)

| Sub-area | Total | Train | Test |
|---|--:|--:|--:|
| AnomalyDetection | 49 | 39 | 10 |
| BlindSourceSeparation | 49 | 39 | 10 |
| CompressedSensing | 49 | 39 | 10 |
| Denoising | 50 | 40 | 10 |
| FaultDetection | 50 | 40 | 10 |
| RadarSonar | 45 | 36 | 9 |
| SpeechAudio | 48 | 38 | 10 |
| TimeSeriesForecasting | 50 | 40 | 10 |

Each record matches `bridgescout.ingestion.preprocessing.Paper` (`limitations_text` / `method_text` mirror the abstract), plus `sub_area`, `url`, `doi`, `pdf_path`, `pdf_source`, `split`.
