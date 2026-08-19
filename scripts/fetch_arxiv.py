"""Optional helper: pull real papers from the public arXiv API into a JSON file
that can be merged into the sample corpus via `build_index.py --extra`.

Note: arXiv only gives us title + abstract, not a clean split between a paper's
"limitation" and "method" sections, so both `limitations_text` and `method_text`
are set to the abstract as an approximation.
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridgescout.config import DATA_DIR

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_arxiv_papers(query: str, max_results: int = 5, domain_label: str = "") -> list[dict]:
    params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results}
    response = requests.get(ARXIV_API_URL, params=params, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.text)

    papers = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = entry.find("atom:title", ATOM_NS).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ATOM_NS).text.strip().replace("\n", " ")
        arxiv_id = entry.find("atom:id", ATOM_NS).text.strip().rsplit("/", 1)[-1]
        papers.append(
            {
                "id": f"arxiv-{arxiv_id}",
                "title": title,
                "domain": domain_label or query,
                "abstract": summary,
                "limitations_text": summary,
                "method_text": summary,
            }
        )
    return papers


def main():
    parser = argparse.ArgumentParser(description="Fetch sample papers from the arXiv API.")
    parser.add_argument("query", help="arXiv search query, e.g. 'few-shot learning'")
    parser.add_argument("--domain", default="", help="Domain label to assign to fetched papers")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument(
        "--out",
        default=str(DATA_DIR / "sample_papers" / "arxiv_fetched.json"),
        help="Output JSON file",
    )
    args = parser.parse_args()

    papers = fetch_arxiv_papers(args.query, args.max_results, args.domain)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2)
    print(f"Fetched {len(papers)} papers -> {out_path}")


if __name__ == "__main__":
    main()
