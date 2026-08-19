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
