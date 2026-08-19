import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridgescout.cross_domain_search.vector_store import VectorStore
from bridgescout.ingestion.preprocessing import Paper, load_sample_papers


def main():
    parser = argparse.ArgumentParser(description="Build the BridgeScout FAISS index from sample papers.")
    parser.add_argument(
        "--extra",
        help="Optional path to an extra papers JSON file (e.g. arxiv_fetched.json) to merge in",
        default=None,
    )
    args = parser.parse_args()

    papers = load_sample_papers()
    if args.extra:
        with open(args.extra, "r", encoding="utf-8") as f:
            extra_records = json.load(f)
        papers.extend(Paper(**record) for record in extra_records)

    store = VectorStore()
    store.build(papers)
    store.save()
    print(f"Indexed {len(store.metadata)} candidate papers -> data/index/")


if __name__ == "__main__":
    main()
