# BridgeScout — A Cross-Domain Research Gap Discovery System

BridgeScout extracts unresolved problems, limitations, and future-work
statements from research papers, converts them into domain-neutral semantic
representations, and searches across *other* disciplines for related
solutions — ranking candidates with a "bridge score."

This repo is an MVP implementation of the 6-module architecture:

```
Research Papers -> Text Preprocessing -> LLM-based Gap Detection
  -> Semantic Mapping -> Cross-Domain Search -> Bridge Score Calculation
  -> Recommendation Dashboard
```

The Recommendation Dashboard (Module 6) is a **React + TypeScript** single-page
app backed by a thin **FastAPI** HTTP layer over the same Python pipeline used
by the CLI — the API layer adds no new business logic, it just exposes
`bridgescout/*` over HTTP for the browser.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # optional: add ANTHROPIC_API_KEY for LLM-based extraction
```

The first run downloads the `all-MiniLM-L6-v2` sentence-transformers model
(~80 MB) from Hugging Face, so an internet connection is needed at least once.

## Running it

Build the FAISS index from the bundled sample papers:

```bash
python scripts/build_index.py
```

Run the pipeline on one sample paper from the terminal:

```bash
python scripts/run_pipeline.py --list
python scripts/run_pipeline.py --paper medicine-ecg-arrhythmia
```

Launch the dashboard — two terminals:

```bash
# Terminal 1: API backend
uvicorn bridgescout.api.app:app --reload --port 8000

# Terminal 2: React frontend
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`). Pick a bundled
sample paper (or upload your own PDF via the sidebar), and each detected
research gap gets its own tab with nested tabs for its ranked cross-domain
recommendations, each with a bridge-score meter.

Run the tests:

```bash
pytest tests/
```

## Module map

| Module | Code |
|---|---|
| 1. Research Paper Collection | `bridgescout/ingestion/` |
| 2. LLM-based Gap Detection | `bridgescout/gap_detection/` |
| 3. Semantic Mapping | `bridgescout/semantic_mapping/` |
| 4. Cross-Domain Search | `bridgescout/cross_domain_search/` |
| 5. Bridge Score Calculation | `bridgescout/bridge_scoring/` |
| 6. Recommendation Dashboard | `frontend/` (React UI) + `bridgescout/api/` (FastAPI backend) |

`bridgescout/pipeline.py` wires modules 1–5 together as
`BridgeScoutPipeline.run(paper) -> list[Recommendation]` for the CLI scripts.
`bridgescout/api/app.py` wires the same underlying functions together for the
web UI via a single `POST /api/analyze` call per paper (see
`bridgescout/api/schemas.py` for the request/response shape).

## Design notes / simplifications from the original proposal

- **LLM gap extraction is pluggable.** If `ANTHROPIC_API_KEY` is set,
  `AnthropicLLMClient` (`bridgescout/gap_detection/llm_client.py`) calls
  Claude to extract limitation/future-work statements and to paraphrase them
  into domain-neutral problem statements. If no key is set, a
  `HeuristicLLMClient` (cue-phrase sentence matching, e.g. "however",
  "limitation", "future work") is used instead, so the whole pipeline runs
  fully offline with no API cost. This is a deliberate simplification to
  keep the MVP runnable without a paid API key — swap in the Anthropic
  client for higher-quality extraction in the actual demo/review.
- **Storage uses FAISS + local JSON**, not PostgreSQL/MongoDB as listed in
  the original hardware/software requirements slide. This avoids needing to
  stand up and manage a database server for the prototype. Paper metadata
  lives in `data/sample_papers/papers.json`; the built vector index and its
  metadata are written to `data/index/` (gitignored, rebuilt via
  `scripts/build_index.py`). Migrating to Postgres/Mongo + a managed vector
  store (e.g. pgvector, ChromaDB) is a reasonable next step for a
  production version.
- **Dashboard is React + FastAPI, not Streamlit.** The project started with
  a Streamlit dashboard and later moved to a React SPA over a small FastAPI
  backend for a more customizable, production-style UI (tabs, badges,
  bridge-score meters). The API is stateless — the frontend holds the full
  paper object and posts it back on each call — and every endpoint in
  `bridgescout/api/app.py` calls straight into the same `bridgescout/*`
  modules the CLI uses, so there is exactly one implementation of the
  pipeline logic.
- **Sample corpus**: `data/sample_papers/papers.json` bundles 8 papers
  spanning 8 distinct domains (NLP, Robotics, Medicine, Energy Systems,
  Civil Engineering, Materials Science, Computer Vision, Agriculture), each
  hand-written with a clear limitation statement and a method/solution
  description, chosen so that several genuinely make sense as cross-domain
  matches (e.g. the ECG noise-robustness gap in Medicine matches the
  sensor-denoising method in Energy Systems; the low-light labeled-data
  scarcity gap in Computer Vision matches the few-shot/synthetic-data method
  in Agriculture). `scripts/fetch_arxiv.py` can optionally pull real papers
  from the arXiv API (title + abstract only) into a separate JSON file,
  which can be merged in via `python scripts/build_index.py --extra <path>`.
- **Bridge score** = `0.7 * cosine_similarity + 0.3 * cross_domain_bonus`
  (weights in `bridgescout/config.py`), where the bonus rewards candidates
  from a different domain than the source paper — this is what pushes
  results toward genuinely cross-domain matches rather than plain nearest-
  neighbor search.
