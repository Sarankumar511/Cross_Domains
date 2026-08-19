from bridgescout.gap_detection.extractor import extract_gaps_for_paper
from bridgescout.gap_detection.llm_client import HeuristicLLMClient
from bridgescout.ingestion.preprocessing import Paper


def test_heuristic_extracts_cue_sentences():
    client = HeuristicLLMClient()
    text = (
        "This method works well on the benchmark dataset. "
        "However, it fails to generalize to unseen domains and future work should "
        "explore adaptation techniques."
    )
    gaps = client.extract_gaps(text)
    assert any("however" in g.lower() or "future work" in g.lower() for g in gaps)


def test_extract_gaps_for_paper_uses_limitations_text():
    paper = Paper(
        id="p1",
        title="Test Paper",
        domain="Testing",
        limitations_text=(
            "However, the approach does not scale well. Future work should address "
            "scalability."
        ),
    )
    gaps = extract_gaps_for_paper(paper, llm_client=HeuristicLLMClient())
    assert len(gaps) >= 1
    assert all(g.paper_id == "p1" for g in gaps)
