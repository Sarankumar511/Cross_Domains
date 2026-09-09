from __future__ import annotations

from pydantic import BaseModel


class PaperModel(BaseModel):
    id: str
    title: str
    domain: str
    abstract: str = ""
    authors: str = ""
    year: int | None = None
    limitations_text: str = ""
    method_text: str = ""
    source: str = "sample"
    # Set on the /api/papers listing so the sidebar can tag each row.
    # "train" / "test" (collected corpus), "uploaded" (admin), "sample" (bundled seed).
    split: str = ""
    sub_area: str = ""


class AnalyzeRequest(BaseModel):
    paper: PaperModel


class CandidateModel(BaseModel):
    title: str
    domain: str
    similarity: float


class RecommendationModel(BaseModel):
    title: str
    short_title: str
    domain: str
    similarity: float
    domain_bonus: float
    bridge_score: float
    rationale: str
    method_text: str
    status_label: str


class GapResult(BaseModel):
    index: int
    text: str
    short_title: str
    headline: str
    generic_text: str
    candidates: list[CandidateModel]
    recommendations: list[RecommendationModel]


class AnalyzeResponse(BaseModel):
    gaps: list[GapResult]


class CreateDomainRequest(BaseModel):
    name: str


class IndexStatus(BaseModel):
    state: str  # "ready" | "training" | "error"
    papers: int = 0
    passages: int = 0
    error: str | None = None


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskMatch(BaseModel):
    paper_id: str
    paper_title: str
    domain: str
    snippet: str
    score: float


class AskResponse(BaseModel):
    question: str
    answer_found: bool
    matches: list[AskMatch]
