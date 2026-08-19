from bridgescout.bridge_scoring.scorer import compute_bridge_score
from bridgescout.config import CROSS_DOMAIN_BONUS, DOMAIN_WEIGHT, SAME_DOMAIN_PENALTY, SIMILARITY_WEIGHT


def test_cross_domain_scores_higher_than_same_domain_for_equal_similarity():
    cross_score, cross_bonus = compute_bridge_score(0.8, "NLP", "Robotics")
    same_score, same_bonus = compute_bridge_score(0.8, "NLP", "NLP")
    assert cross_bonus == CROSS_DOMAIN_BONUS
    assert same_bonus == SAME_DOMAIN_PENALTY
    assert cross_score > same_score


def test_score_formula():
    score, bonus = compute_bridge_score(0.5, "A", "B")
    assert bonus == CROSS_DOMAIN_BONUS
    assert score == SIMILARITY_WEIGHT * 0.5 + DOMAIN_WEIGHT * CROSS_DOMAIN_BONUS
