from __future__ import annotations

from dataclasses import dataclass

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
    gap_texts = client.extract_gaps(source_text)
    return [Gap(paper_id=paper.id, text=text) for text in gap_texts]
