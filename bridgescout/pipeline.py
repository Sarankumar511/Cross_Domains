from __future__ import annotations

from bridgescout.bridge_scoring.scorer import Recommendation, build_recommendation
from bridgescout.config import FAISS_INDEX_PATH, TOP_K_RESULTS
from bridgescout.cross_domain_search.search import search_cross_domain
from bridgescout.cross_domain_search.vector_store import VectorStore
from bridgescout.gap_detection.extractor import extract_gaps_for_paper
from bridgescout.gap_detection.llm_client import LLMClient, get_llm_client
from bridgescout.ingestion.preprocessing import Paper, load_sample_papers
from bridgescout.semantic_mapping.normalizer import normalize_gap


class BridgeScoutPipeline:
    def __init__(self, vector_store: VectorStore | None = None, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or get_llm_client()
        self.vector_store = vector_store or self._load_or_build_store()

    def _load_or_build_store(self) -> VectorStore:
        store = VectorStore()
        if FAISS_INDEX_PATH.exists():
            store.load()
        else:
            store.build(load_sample_papers())
            store.save()
        return store

    def run(self, paper: Paper, top_k: int = TOP_K_RESULTS) -> list[Recommendation]:
        gaps = extract_gaps_for_paper(paper, self.llm_client)
        recommendations: list[Recommendation] = []
        for gap in gaps:
            neutral_gap = normalize_gap(gap, paper.domain, self.llm_client)
            candidates = search_cross_domain(
                self.vector_store, neutral_gap, paper.domain, paper.id, top_k=top_k
            )
            for meta, similarity in candidates:
                recommendations.append(
                    build_recommendation(paper.id, paper.domain, neutral_gap, meta, similarity)
                )
        recommendations.sort(key=lambda r: r.bridge_score, reverse=True)
        return recommendations
