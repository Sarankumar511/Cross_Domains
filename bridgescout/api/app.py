from __future__ import annotations

import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from bridgescout.api.formatting import clean_gap_title, gap_headline, score_status_label, short_title
from bridgescout.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CandidateModel,
    GapResult,
    PaperModel,
    RecommendationModel,
)
from bridgescout.bridge_scoring.scorer import build_recommendation
from bridgescout.config import FAISS_INDEX_PATH, TOP_K_RESULTS
from bridgescout.cross_domain_search.search import search_cross_domain
from bridgescout.cross_domain_search.vector_store import VectorStore
from bridgescout.gap_detection.extractor import extract_gaps_for_paper
from bridgescout.gap_detection.llm_client import get_llm_client
from bridgescout.ingestion.preprocessing import Paper, load_pdf_as_paper, load_sample_papers
from bridgescout.semantic_mapping.normalizer import normalize_gap

app = FastAPI(title="BridgeScout API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_llm_client = get_llm_client()
_vector_store = VectorStore()


@app.on_event("startup")
def _startup() -> None:
    if FAISS_INDEX_PATH.exists():
        _vector_store.load()
    else:
        _vector_store.build(load_sample_papers())
        _vector_store.save()


def _to_paper(model: PaperModel) -> Paper:
    return Paper(**model.model_dump())


@app.get("/api/papers", response_model=list[PaperModel])
def list_papers() -> list[PaperModel]:
    return [PaperModel(**vars(p)) for p in load_sample_papers()]


@app.post("/api/papers/upload", response_model=PaperModel)
async def upload_paper(file: UploadFile = File(...), domain: str = Form("Unknown")) -> PaperModel:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    paper = load_pdf_as_paper(tmp_path, title=file.filename, domain=domain)
    return PaperModel(**vars(paper))


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_paper(request: AnalyzeRequest) -> AnalyzeResponse:
    paper = _to_paper(request.paper)
    gaps = extract_gaps_for_paper(paper, _llm_client)

    gap_results: list[GapResult] = []
    for index, gap in enumerate(gaps):
        neutral_gap = normalize_gap(gap, paper.domain, _llm_client)
        raw_candidates = search_cross_domain(
            _vector_store, neutral_gap, paper.domain, paper.id, top_k=TOP_K_RESULTS
        )

        recommendations = [
            build_recommendation(paper.id, paper.domain, neutral_gap, meta, similarity)
            for meta, similarity in raw_candidates
        ]
        recommendations.sort(key=lambda r: r.bridge_score, reverse=True)

        gap_results.append(
            GapResult(
                index=index,
                text=gap.text,
                short_title=short_title(clean_gap_title(gap.text), max_len=32),
                headline=gap_headline(gap.text),
                generic_text=neutral_gap.generic_text,
                candidates=[
                    CandidateModel(title=meta["title"], domain=meta["domain"], similarity=similarity)
                    for meta, similarity in raw_candidates
                ],
                recommendations=[
                    RecommendationModel(
                        title=r.candidate_title,
                        short_title=short_title(r.candidate_title, max_len=28),
                        domain=r.candidate_domain,
                        similarity=r.similarity,
                        domain_bonus=r.domain_bonus,
                        bridge_score=r.bridge_score,
                        rationale=r.rationale,
                        method_text=r.candidate_method_text,
                        status_label=score_status_label(r.bridge_score),
                    )
                    for r in recommendations
                ],
            )
        )

    return AnalyzeResponse(gaps=gap_results)
