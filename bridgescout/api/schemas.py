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
