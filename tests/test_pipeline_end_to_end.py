from bridgescout.cross_domain_search.vector_store import VectorStore
from bridgescout.gap_detection.llm_client import HeuristicLLMClient
from bridgescout.ingestion.preprocessing import load_sample_papers
from bridgescout.pipeline import BridgeScoutPipeline


def test_pipeline_produces_cross_domain_recommendations():
    papers = load_sample_papers()
    store = VectorStore()
    store.build(papers)

    pipeline = BridgeScoutPipeline(vector_store=store, llm_client=HeuristicLLMClient())

    source_paper = next(p for p in papers if p.id == "medicine-ecg-arrhythmia")
    recommendations = pipeline.run(source_paper)

    assert len(recommendations) > 0
    assert all(rec.candidate_domain != source_paper.domain for rec in recommendations)
    assert recommendations == sorted(recommendations, key=lambda r: r.bridge_score, reverse=True)
