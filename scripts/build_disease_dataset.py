"""Phase 1 dataset builder: collect the ``Disease`` domain corpus.

Pulls papers from PubMed + arXiv across eight disease sub-areas, downloads the
open-access PDFs, and writes an 80/20 stratified train/test split under
``dataset/Disease/``.

Examples
--------
    python scripts/build_disease_dataset.py
    python scripts/build_disease_dataset.py --per-area 20 --no-pdfs
    python scripts/build_disease_dataset.py --areas Cardiovascular Oncology --per-area 10
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridgescout.config import DISEASE_DATASET_DIR, NCBI_API_KEY
from bridgescout.datasets.disease import DISEASE_AREAS, build_disease_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-area", type=int, default=50, help="Target papers per disease area (default 50)")
    parser.add_argument(
        "--pubmed-share",
        type=float,
        default=0.5,
        help="Fraction of each area's quota taken from PubMed vs arXiv (default 0.5)",
    )
    parser.add_argument("--test-ratio", type=float, default=0.2, help="Held-out test fraction (default 0.2)")
    parser.add_argument("--seed", type=int, default=42, help="Split RNG seed (default 42)")
    parser.add_argument(
        "--areas",
        nargs="+",
        metavar="AREA",
        default=None,
        help=f"Subset of areas to build. Choices: {', '.join(DISEASE_AREAS)}",
    )
    parser.add_argument("--no-pdfs", action="store_true", help="Skip open-access PDF downloads")
    parser.add_argument(
        "--out",
        default=str(DISEASE_DATASET_DIR),
        help="Output directory (default: dataset/Disease/)",
    )
    parser.add_argument("--arxiv-pause", type=float, default=3.0, help="Seconds between arXiv calls (be polite)")
    args = parser.parse_args()

    manifest = build_disease_dataset(
        out_dir=Path(args.out),
        per_area=args.per_area,
        pubmed_share=args.pubmed_share,
        test_ratio=args.test_ratio,
        seed=args.seed,
        download_pdf=not args.no_pdfs,
        areas=args.areas,
        api_key=NCBI_API_KEY,
        arxiv_pause=args.arxiv_pause,
    )

    totals = manifest["totals"]
    print("\n=== Summary ===")
    print(f"Records : {totals['records']}  (PubMed {manifest['by_source']['pubmed']}, arXiv {manifest['by_source']['arxiv']})")
    print(f"Split   : {totals['train']} train / {totals['test']} test")
    print(f"PDFs    : {totals['with_pdf']} ({totals['pdf_coverage'] * 100:.0f}% coverage)")
    print(f"Output  : {args.out}")
    for area, count in sorted(manifest["records_by_area"].items()):
        tr = manifest["train_by_area"].get(area, 0)
        te = manifest["test_by_area"].get(area, 0)
        print(f"  {area:<20} {count:>4}  ({tr} train / {te} test)")


if __name__ == "__main__":
    main()
