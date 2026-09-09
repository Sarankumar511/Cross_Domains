"""Generic dataset builder: collect any registered domain the same way as Disease.

Fetch (arXiv + OpenAlex, or PubMed + arXiv for Disease) -> dedupe -> download
open-access PDFs -> reproducible stratified 80/20 train/test split, written to
``dataset/<Domain>/``.

Examples
--------
    python scripts/build_dataset.py --domain all
    python scripts/build_dataset.py --domain SignalProcessing EarthEnvironment
    python scripts/build_dataset.py --domain Finance --per-area 20 --no-pdfs
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridgescout.config import DATASET_DIR, NCBI_API_KEY
from bridgescout.datasets.builder import build_domain_dataset
from bridgescout.datasets.registry import DOMAINS, METHOD_DOMAINS


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--domain",
        nargs="+",
        required=True,
        metavar="NAME",
        help=f"One or more of {list(DOMAINS)}, or 'all' (every domain), "
        f"or 'method' (the five non-Disease domains).",
    )
    parser.add_argument("--per-area", type=int, default=50, help="Target papers per sub-area (default 50)")
    parser.add_argument("--test-ratio", type=float, default=0.2, help="Held-out fraction (default 0.2)")
    parser.add_argument("--seed", type=int, default=42, help="Split RNG seed (default 42)")
    parser.add_argument("--areas", nargs="+", default=None, help="Restrict to these sub-areas")
    parser.add_argument("--no-pdfs", action="store_true", help="Skip open-access PDF downloads")
    parser.add_argument(
        "--arxiv-pdfs-only",
        action="store_true",
        help="Only fetch arXiv PDFs; skip the slow/flaky OpenAlex and PMC routes",
    )
    parser.add_argument(
        "--out-root",
        default=str(DATASET_DIR),
        help="Parent directory for <Domain>/ folders (default: dataset/)",
    )
    args = parser.parse_args()

    selected = _resolve_domains(args.domain)
    out_root = Path(args.out_root)
    summaries = []
    for name in selected:
        spec = DOMAINS[name]
        print(f"\n{'=' * 60}\n{name}  (sources: {', '.join(spec.sources)})\n{'=' * 60}")
        manifest = build_domain_dataset(
            domain=spec.name,
            area_queries=spec.areas,
            out_dir=out_root / spec.name,
            source_names=spec.sources,
            per_area=args.per_area,
            test_ratio=args.test_ratio,
            seed=args.seed,
            download_pdf=not args.no_pdfs,
            pdf_skip_sources=("oa-url", "pmc-oa") if args.arxiv_pdfs_only else (),
            areas=args.areas,
            api_key=NCBI_API_KEY,
        )
        summaries.append((name, manifest))

    print(f"\n{'=' * 60}\nDONE\n{'=' * 60}")
    for name, manifest in summaries:
        totals = manifest["totals"]
        by_source = ", ".join(f"{k} {v}" for k, v in sorted(manifest["by_source"].items()))
        print(
            f"{name:<24} {totals['records']:>4} records  "
            f"({totals['train']} train / {totals['test']} test)  "
            f"PDFs {totals['with_pdf']} ({totals['pdf_coverage'] * 100:.0f}%)  [{by_source}]"
        )


def _resolve_domains(requested: list[str]) -> list[str]:
    if any(token.lower() == "all" for token in requested):
        return list(DOMAINS)
    if any(token.lower() == "method" for token in requested):
        return list(METHOD_DOMAINS)
    unknown = [token for token in requested if token not in DOMAINS]
    if unknown:
        parser_choices = list(DOMAINS) + ["all", "method"]
        raise SystemExit(f"Unknown domain(s): {unknown}. Choices: {parser_choices}")
    return requested


if __name__ == "__main__":
    main()
