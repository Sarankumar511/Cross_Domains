from __future__ import annotations

from dataclasses import dataclass

from bridgescout.config import MAX_ANALYZE_GAPS, MAX_GAP_SOURCE_CHARS
from bridgescout.gap_detection.llm_client import LLMClient, get_llm_client
from bridgescout.ingestion.preprocessing import Paper


@dataclass
class Gap:
    paper_id: str
    text: str


def extract_gaps_for_paper(paper: Paper, llm_client: LLMClient | None = None) -> list[Gap]:
    client = llm_client or get_llm_client()
    source_text = paper.limitations_text or paper.abstract
    if not source_text:
        return []
    # A whole uploaded PDF can be tens of thousands of characters; scanning all
    # of it (and analysing every cue-phrase hit) is what makes /api/analyze slow.
    source_text = source_text[:MAX_GAP_SOURCE_CHARS]
    gap_texts = client.extract_gaps(source_text)[:MAX_ANALYZE_GAPS]
    return [Gap(paper_id=paper.id, text=text) for text in gap_texts]
