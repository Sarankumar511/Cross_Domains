from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from bridgescout.config import MAX_GAP_SOURCE_CHARS, SAMPLE_PAPERS_PATH

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class Paper:
    id: str
    title: str
    domain: str
    abstract: str = ""
    authors: str = ""
    year: int | None = None
    # Raw text to run gap/limitation extraction on (e.g. discussion/conclusion section).
    limitations_text: str = ""
    # Text describing the paper's method/solution; used as searchable content
    # when this paper is a cross-domain candidate.
    method_text: str = ""
    source: str = "sample"


def clean_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def load_sample_papers() -> list[Paper]:
    with open(SAMPLE_PAPERS_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    return [Paper(source="sample", **record) for record in records]


def load_pdf_as_paper(pdf_path: str, title: str | None = None, domain: str = "Unknown") -> Paper:
    from bridgescout.ingestion.pdf_loader import extract_text_from_pdf

    raw_text = extract_text_from_pdf(pdf_path)
    cleaned = clean_text(raw_text)
    paper_id = re.sub(r"[^a-z0-9]+", "-", (title or pdf_path).lower()).strip("-")
    return Paper(
        id=paper_id or "uploaded-paper",
        title=title or paper_id,
        domain=domain,
        abstract=cleaned[:500],
        # Gap extraction only scans the first MAX_GAP_SOURCE_CHARS anyway; keeping
        # the whole PDF text here just bloats the API response and the sidebar.
        limitations_text=cleaned[:MAX_GAP_SOURCE_CHARS],
        method_text="",
        source="pdf",
    )
