import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridgescout.ingestion.preprocessing import load_sample_papers
from bridgescout.pipeline import BridgeScoutPipeline


def main():
    parser = argparse.ArgumentParser(description="Run the BridgeScout pipeline on a sample paper.")
    parser.add_argument("--paper", help="Paper id from data/sample_papers/papers.json", default=None)
    parser.add_argument("--list", action="store_true", help="List available sample paper ids")
    args = parser.parse_args()

    papers = load_sample_papers()
    if args.list or not args.paper:
        print("Available paper ids:")
        for p in papers:
            print(f"  {p.id}  ({p.domain}) - {p.title}")
        if not args.paper:
            return

    paper = next((p for p in papers if p.id == args.paper), None)
    if paper is None:
        print(f"Unknown paper id: {args.paper}")
        return

    pipeline = BridgeScoutPipeline()
    recommendations = pipeline.run(paper)

    print(f"\nSource paper: {paper.title} ({paper.domain})\n")
    if not recommendations:
        print("No cross-domain recommendations found.")
        return

    for rec in recommendations:
        print(f"- Gap: {rec.gap_text}")
        print(f"  Generic problem: {rec.generic_gap_text}")
        print(
            f"  -> {rec.candidate_title} [{rec.candidate_domain}] "
            f"bridge_score={rec.bridge_score:.2f} similarity={rec.similarity:.2f}"
        )
        print(f"     {rec.candidate_method_text}")
        print()


if __name__ == "__main__":
    main()
