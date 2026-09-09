from __future__ import annotations

from bridgescout.config import TOP_K_RESULTS
from bridgescout.cross_domain_search.vector_store import VectorStore
from bridgescout.semantic_mapping.normalizer import DomainNeutralGap


def search_cross_domain(
    store: VectorStore,
    gap: DomainNeutralGap,
    source_domain: str,
    source_paper_id: str,
    top_k: int = TOP_K_RESULTS,
    exclude_same_domain: bool = True,
    allowed_ids: set[str] | None = None,
) -> list[tuple[dict, float]]:
    # Over-fetch, since candidates from the source paper/domain (and any the caller
    # has since deleted) get filtered out below.
    raw_results = store.search(gap.embedding, top_k=top_k * 4 + 10)
    filtered: list[tuple[dict, float]] = []
    for meta, score in raw_results:
        if meta["paper_id"] == source_paper_id:
            continue
        if exclude_same_domain and meta["domain"] == source_domain:
            continue
        if allowed_ids is not None and meta["paper_id"] not in allowed_ids:
            continue
        filtered.append((meta, score))
        if len(filtered) >= top_k:
            break
    return filtered
