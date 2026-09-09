# Finance dataset

Generated: 2026-09-07T10:12:20+00:00

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

- Records: **391** (arxiv (196), openalex (195))
- Train / Test: **313 / 78**
- With PDF: **189** (48% coverage)

## Records by sub-area (train / test)

| Sub-area | Total | Train | Test |
|---|--:|--:|--:|
| AlgorithmicTrading | 50 | 40 | 10 |
| CreditRiskScoring | 50 | 40 | 10 |
| FinancialNLP | 48 | 38 | 10 |
| FraudDetection | 50 | 40 | 10 |
| MarketAnomalyDetection | 47 | 38 | 9 |
| PortfolioOptimization | 50 | 40 | 10 |
| RiskManagement | 47 | 38 | 9 |
| StockForecasting | 49 | 39 | 10 |

Each record matches `bridgescout.ingestion.preprocessing.Paper` (`limitations_text` / `method_text` mirror the abstract), plus `sub_area`, `url`, `doi`, `pdf_path`, `pdf_source`, `split`.
