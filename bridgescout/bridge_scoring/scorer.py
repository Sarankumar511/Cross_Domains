from __future__ import annotations

from dataclasses import dataclass

from bridgescout.config import CROSS_DOMAIN_BONUS, DOMAIN_WEIGHT, SAME_DOMAIN_PENALTY, SIMILARITY_WEIGHT
from bridgescout.semantic_mapping.normalizer import DomainNeutralGap


@dataclass
class Recommendation:
    source_paper_id: str
    gap_text: str
    generic_gap_text: str
    candidate_paper_id: str
    candidate_title: str
    candidate_domain: str
    candidate_method_text: str
    similarity: float
    domain_bonus: float
    bridge_score: float
    rationale: str


def compute_bridge_score(similarity: float, source_domain: str, candidate_domain: str) -> tuple[float, float]:
    domain_bonus = CROSS_DOMAIN_BONUS if candidate_domain != source_domain else SAME_DOMAIN_PENALTY
    score = SIMILARITY_WEIGHT * similarity + DOMAIN_WEIGHT * domain_bonus
    return score, domain_bonus


def build_recommendation(
    source_paper_id: str,
    source_domain: str,
    gap: DomainNeutralGap,
    candidate_meta: dict,
    similarity: float,
) -> Recommendation:
    score, domain_bonus = compute_bridge_score(similarity, source_domain, candidate_meta["domain"])
    rationale = (
        f"Semantic similarity {similarity:.2f} between the generalized problem and "
        f"'{candidate_meta['title']}' ({candidate_meta['domain']})"
        + (
            ", plus a cross-domain bonus since the solution comes from a different field."
            if domain_bonus > 0
            else "."
        )
    )
    return Recommendation(
        source_paper_id=source_paper_id,
        gap_text=gap.original_text,
        generic_gap_text=gap.generic_text,
        candidate_paper_id=candidate_meta["paper_id"],
        candidate_title=candidate_meta["title"],
        candidate_domain=candidate_meta["domain"],
        candidate_method_text=candidate_meta["method_text"],
        similarity=similarity,
        domain_bonus=domain_bonus,
        bridge_score=score,
        rationale=rationale,
    )
