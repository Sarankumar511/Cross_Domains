from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bridgescout.gap_detection.extractor import Gap
from bridgescout.gap_detection.llm_client import LLMClient, get_llm_client
from bridgescout.semantic_mapping.embedder import embed_text


@dataclass
class DomainNeutralGap:
    paper_id: str
    original_text: str
    generic_text: str
    embedding: np.ndarray


def normalize_gap(gap: Gap, domain: str, llm_client: LLMClient | None = None) -> DomainNeutralGap:
    client = llm_client or get_llm_client()
    generic_text = client.paraphrase_generic(gap.text, domain) or gap.text
    embedding = embed_text(generic_text)
    return DomainNeutralGap(
        paper_id=gap.paper_id,
        original_text=gap.text,
        generic_text=generic_text,
        embedding=embedding,
    )
