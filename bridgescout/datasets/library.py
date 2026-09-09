"""Load the collected train/test corpora as pipeline ``Paper`` objects.

``scripts/build_dataset.py`` writes one folder per domain under ``dataset/``:
``dataset/<Domain>/{train,test,all_papers}.json`` plus ``pdfs/<id>.pdf`` for the
open-access full texts. This module reads those back so the admin paper library
and the search indexes can include every paper the project trained and tested on,
grouped under its domain folder in the sidebar.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from bridgescout.config import DATA_DIR, DATASET_DIR
from bridgescout.ingestion.preprocessing import Paper

# A small id -> {split, sub_area, domain} map covering every collected paper.
# Written by scripts/build_corpus_index.py and shipped in the droplet (unlike the
# multi-GB dataset/ folder), so the deployed backend can still tag a paper loaded
# into HANA as 'train' / 'test' and show its sub-area.
CORPUS_INDEX_PATH = DATA_DIR / "corpus_index.json"

_PAPER_KEYS = (
    "id", "title", "domain", "abstract", "authors", "year",
    "limitations_text", "method_text", "source",
)


def _record_to_paper(record: dict) -> Paper:
    fields = {k: record.get(k) for k in _PAPER_KEYS if record.get(k) is not None}
    fields.setdefault("id", record.get("id", ""))
    fields.setdefault("title", record.get("title", fields["id"]))
    fields.setdefault("domain", record.get("domain", "Uncategorised"))
    return Paper(**fields)


@lru_cache(maxsize=1)
def load_corpus_papers() -> tuple[tuple[Paper, dict], ...]:
    """Every collected paper as ``(Paper, meta)`` where meta carries
    ``split`` ('train'|'test'), ``sub_area`` and ``pdf_path`` (relative to the
    domain folder, '' when there is no local PDF)."""
    if not DATASET_DIR.exists():
        return ()

    out: list[tuple[Paper, dict]] = []
    for domain_dir in sorted(p for p in DATASET_DIR.iterdir() if p.is_dir()):
        records: list[dict] = []
        seen: set[str] = set()
        for split in ("train", "test"):
            path = domain_dir / f"{split}.json"
            if not path.exists():
                continue
            for record in json.loads(path.read_text(encoding="utf-8")):
                record["_split"] = record.get("split") or split
                records.append(record)
                seen.add(record.get("id", ""))

        if not records:
            path = domain_dir / "all_papers.json"
            if path.exists():
                for record in json.loads(path.read_text(encoding="utf-8")):
                    record["_split"] = record.get("split") or ""
                    records.append(record)

        for record in records:
            paper = _record_to_paper(record)
            if not paper.id:
                continue
            rel_pdf = record.get("pdf_path") or ""
            abs_pdf = ""
            if rel_pdf:
                candidate = domain_dir / rel_pdf
                if candidate.exists():
                    abs_pdf = str(candidate)
            out.append(
                (
                    paper,
                    {
                        "split": record.get("_split", ""),
                        "sub_area": record.get("sub_area", ""),
                        "pdf_path": abs_pdf,
                    },
                )
            )
    return tuple(out)


def corpus_pdf_path(paper_id: str) -> Path | None:
    for paper, meta in load_corpus_papers():
        if paper.id == paper_id and meta["pdf_path"]:
            return Path(meta["pdf_path"])
    return None


@lru_cache(maxsize=1)
def load_corpus_index() -> dict[str, dict]:
    """id -> {'split', 'sub_area', 'domain'} for every collected paper.

    Prefers the on-disk ``dataset/`` folders (local dev, full metadata); falls
    back to the shipped ``data/corpus_index.json`` (Cloud Foundry, where
    ``dataset/`` is not in the droplet). Empty when neither is present.
    """
    from_disk = {
        paper.id: {"split": meta["split"], "sub_area": meta["sub_area"], "domain": paper.domain}
        for paper, meta in load_corpus_papers()
    }
    if from_disk:
        return from_disk
    if CORPUS_INDEX_PATH.exists():
        try:
            raw = json.loads(CORPUS_INDEX_PATH.read_text(encoding="utf-8"))
            return {str(k): dict(v) for k, v in raw.items()}
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    return {}


def write_corpus_index(path: Path = CORPUS_INDEX_PATH) -> int:
    """(Re)generate the shipped corpus index from the on-disk dataset folders."""
    index = {
        paper.id: {"split": meta["split"], "sub_area": meta["sub_area"], "domain": paper.domain}
        for paper, meta in load_corpus_papers()
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(index)
