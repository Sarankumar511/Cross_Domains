import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SAMPLE_PAPERS_PATH = DATA_DIR / "sample_papers" / "papers.json"
INDEX_DIR = DATA_DIR / "index"
FAISS_INDEX_PATH = INDEX_DIR / "bridgescout.faiss"
INDEX_METADATA_PATH = INDEX_DIR / "metadata.json"
# Question-answering (content) index over every library paper's sentences, plus a
# fingerprint of the library it was built from so a restart can skip re-embedding.
CONTENT_INDEX_PATH = INDEX_DIR / "content.faiss"
CONTENT_METADATA_PATH = INDEX_DIR / "content_metadata.json"
# Paper ids whose vectors are already in the on-disk indexes: lets a restart load
# the cache and only embed papers added since, and lets a delete skip re-embedding
# entirely (the stale vectors are filtered out at query time).
INDEXED_IDS_PATH = INDEX_DIR / "indexed_ids.json"

# Whether to fold the collected train/test corpora (dataset/<Domain>/) into the
# admin paper library and the search indexes. Set BRIDGESCOUT_CORPUS=0 for a fast
# local boot with only the sample papers + admin uploads.
LOAD_CORPUS = os.getenv("BRIDGESCOUT_CORPUS", "1").strip().lower() not in {"0", "false", "no"}

# Collected raw corpora (research papers grouped by top-level domain), built by
# scripts/build_disease_dataset.py and friends. One subfolder per domain, e.g.
# dataset/Disease/{all_papers.json,train.json,test.json,pdfs/,raw/}.
DATASET_DIR = ROOT_DIR / "dataset"
DISEASE_DATASET_DIR = DATASET_DIR / "Disease"

# Optional NCBI E-utilities key: lifts the PubMed rate limit from 3 to 10 req/s.
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "").strip()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# Bridge score weights: final_score = SIMILARITY_WEIGHT * similarity + DOMAIN_WEIGHT * domain_bonus
SIMILARITY_WEIGHT = 0.7
DOMAIN_WEIGHT = 0.3

# Bonus applied when candidate paper's domain differs from the source paper's domain.
CROSS_DOMAIN_BONUS = 1.0
SAME_DOMAIN_PENALTY = 0.0

TOP_K_RESULTS = 5

# Analysis budget: an uploaded full-text PDF can yield hundreds of cue-phrase
# "gaps"; each one costs an embed + FAISS search + recommendation build, and the
# dashboard shows one tab per gap. Cap both the text scanned and the gaps kept.
MAX_GAP_SOURCE_CHARS = 24000
MAX_ANALYZE_GAPS = 15
