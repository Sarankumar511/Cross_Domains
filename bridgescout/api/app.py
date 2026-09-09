from __future__ import annotations

import html
import json
import os
import re
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response

from bridgescout.api.formatting import clean_gap_title, gap_headline, score_status_label, short_title
from bridgescout.api.security import (
    AUTH_ENABLED,
    is_admin_claims,
    optional_auth,
    require_admin,
    require_auth,
)
from bridgescout.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AskMatch,
    AskRequest,
    AskResponse,
    CandidateModel,
    CreateDomainRequest,
    GapResult,
    IndexStatus,
    PaperModel,
    RecommendationModel,
)
from bridgescout.bridge_scoring.scorer import build_recommendation
from bridgescout.config import (
    CONTENT_INDEX_PATH,
    CONTENT_METADATA_PATH,
    FAISS_INDEX_PATH,
    INDEX_METADATA_PATH,
    INDEXED_IDS_PATH,
    LOAD_CORPUS,
    TOP_K_RESULTS,
)
from bridgescout.cross_domain_search.search import search_cross_domain
from bridgescout.cross_domain_search.vector_store import VectorStore
from bridgescout.datasets.library import (
    corpus_pdf_path,
    load_corpus_index,
    load_corpus_papers,
)
from bridgescout.gap_detection.extractor import extract_gaps_for_paper
from bridgescout.gap_detection.llm_client import get_llm_client
from bridgescout.ingestion.preprocessing import (
    Paper,
    clean_text,
    load_pdf_as_paper,
    load_sample_papers,
)
from bridgescout.qa.content_index import ContentIndex
from bridgescout.semantic_mapping.normalizer import normalize_gap
from bridgescout.storage import PAPER_FIELDS, get_store

app = FastAPI(title="BridgeScout API")

# On BTP the SPA reaches this backend same-origin through the Work Zone approuter
# + destination, so CORS is only needed for local dev / a directly hosted UI.
# Override with CORS_ALLOWED_ORIGINS="https://a.example,https://b.example".
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_allowed_origins = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints that require a valid XSUAA token when auth is enabled (i.e. on BTP).
_protected = [Depends(require_auth)]
# Curator-only endpoints: the paper library (list / view / persist upload / delete).
_admin_only = [Depends(require_admin)]

# Minimum question/passage cosine similarity for /api/ask to treat a passage as
# an actual answer rather than a weak lexical coincidence.
_QA_MIN_SCORE = 0.30


def _read_json_list(path: Path) -> list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write_json_list(path: Path, data: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@lru_cache(maxsize=1)
def _corpus_meta() -> dict[str, dict]:
    """id -> {split, sub_area, pdf_path} for the collected train/test corpora."""
    if not LOAD_CORPUS:
        return {}
    return {paper.id: meta for paper, meta in load_corpus_papers()}


def _indexable_papers() -> list[Paper]:
    """Every paper that belongs in the search indexes: bundled seed + collected
    train/test corpora + admin uploads (uploads win on an id clash). Deletions are
    NOT applied here - they are filtered at query time - so deleting a paper never
    forces a full re-embed and restarts stay fast."""
    by_id: dict[str, Paper] = {}
    for paper in load_sample_papers():
        by_id[paper.id] = paper
    if LOAD_CORPUS:
        for paper, _meta in load_corpus_papers():
            by_id.setdefault(paper.id, paper)
    for paper in get_store().uploaded_papers():
        by_id[paper.id] = paper
    return list(by_id.values())


def _library_papers() -> list[Paper]:
    """What the admin sees: the indexable set minus anything the admin deleted."""
    deleted = get_store().deleted_ids()
    return [p for p in _indexable_papers() if p.id not in deleted]


@lru_cache(maxsize=1)
def _corpus_id_set() -> set[str]:
    return set(_corpus_meta())


def _find_library_paper(paper_id: str) -> Paper | None:
    return next((p for p in _library_papers() if p.id == paper_id), None)


def _paper_as_html(paper: Paper) -> str:
    """Readable HTML rendering for seed papers that have no source PDF."""
    def block(label: str, value: str) -> str:
        if not value:
            return ""
        return f"<h2>{html.escape(label)}</h2><p>{html.escape(value)}</p>"

    meta = " &middot; ".join(
        part for part in (paper.authors or "", str(paper.year or ""), paper.domain or "") if part
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(paper.title)}</title>"
        "<style>body{font:15px/1.6 system-ui,-apple-system,'Segoe UI',sans-serif;"
        "color:#0b0b0b;background:#fff;margin:0;padding:28px;max-width:760px}"
        "h1{font-size:1.4rem;margin:0 0 4px}h2{font-size:1rem;margin:20px 0 4px;color:#1f9d55}"
        ".meta{color:#52514e;font-size:.9rem;margin-bottom:8px}"
        "p{margin:0 0 10px}</style></head><body>"
        f"<h1>{html.escape(paper.title)}</h1>"
        f"<div class='meta'>{html.escape(meta)}</div>"
        f"{block('Abstract', paper.abstract)}"
        f"{block('Stated limitations / future work', paper.limitations_text)}"
        f"{block('Method / solution', paper.method_text)}"
        "</body></html>"
    )


def _all_domains() -> list[str]:
    """Every domain the admin UI should show: custom (possibly empty) + those in use."""
    names = {d for d in get_store().custom_domains()}
    names.update(p.domain for p in _library_papers() if p.domain)
    return sorted(names, key=str.lower)


def _unique_paper_id(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "paper"
    taken = {p.id for p in _library_papers()}
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "auth": "xsuaa" if AUTH_ENABLED else "disabled"}


@app.get("/api/me")
async def whoami(request: Request) -> dict:
    """Identify the caller so the SPA can show or hide the curator paper library."""
    claims = await optional_auth(request)
    return {"authenticated": claims is not None, "is_admin": is_admin_claims(claims)}


_llm_client = get_llm_client()
_vector_store = VectorStore()
_content_index = ContentIndex()
_index_state: dict = {"state": "ready", "papers": 0, "passages": 0, "error": None}


def _sync_indexes() -> None:
    """Bring the on-disk semantic indexes in line with the library, doing the
    least work possible:

    * cache present and already covers every indexable paper -> just load it;
    * cache present but missing some papers (an admin upload) -> load + embed
      only those and append;
    * no cache -> full build.

    Deletions need no work here: a deleted paper's vectors stay in the index and
    are filtered out at query time, and its id stays in ``indexed_ids`` so a
    restart still hits the cache. They drop out at the next full build.
    """
    global _vector_store, _content_index, _index_state
    try:
        want = _indexable_papers()
        want_ids = {p.id for p in want}
        indexed_ids = {str(i) for i in _read_json_list(INDEXED_IDS_PATH)}
        have_cache = (
            indexed_ids
            and FAISS_INDEX_PATH.exists()
            and INDEX_METADATA_PATH.exists()
            and CONTENT_INDEX_PATH.exists()
            and CONTENT_METADATA_PATH.exists()
        )

        method_store = VectorStore()
        content_index = ContentIndex()

        if have_cache:
            method_store.load()
            content_index.load(CONTENT_INDEX_PATH, CONTENT_METADATA_PATH)
            missing = [p for p in want if p.id not in indexed_ids]
            if missing:
                method_store.add(missing)
                content_index.add(
                    missing,
                    sentence_level_ids={p.id for p in missing if p.id not in _corpus_id_set()},
                )
                method_store.save()
                content_index.save(CONTENT_INDEX_PATH, CONTENT_METADATA_PATH)
                _write_json_list(INDEXED_IDS_PATH, sorted(indexed_ids | want_ids))
        else:
            sentence_ids = {p.id for p in want if p.id not in _corpus_id_set()}
            method_store.build(want)
            method_store.save()
            content_index.build(want, sentence_level_ids=sentence_ids)
            content_index.save(CONTENT_INDEX_PATH, CONTENT_METADATA_PATH)
            _write_json_list(INDEXED_IDS_PATH, sorted(want_ids))

        _vector_store = method_store
        _content_index = content_index
        _index_state = {
            "state": "ready",
            "papers": len(_library_papers()),
            "passages": content_index.size(),
            "error": None,
        }
    except Exception as exc:  # keep serving the previous indexes
        _index_state = {**_index_state, "state": "error", "error": str(exc)}


def _schedule_retrain(background_tasks: BackgroundTasks) -> None:
    global _index_state
    _index_state = {**_index_state, "state": "training", "error": None}
    background_tasks.add_task(_sync_indexes)


@app.on_event("startup")
def _startup() -> None:
    _sync_indexes()


def _to_paper(model: PaperModel) -> Paper:
    data = model.model_dump()
    return Paper(**{k: data[k] for k in PAPER_FIELDS})


@app.get("/api/papers", response_model=list[PaperModel], dependencies=_admin_only)
def list_papers() -> list[PaperModel]:
    """Curator-only: the paper library for the domain-folder tree. Each row is
    tagged: 'train' / 'test' (collected corpus), 'uploaded' (admin), 'sample'.

    A collected-corpus paper is tagged from the corpus index even when it lives
    in the store (e.g. bulk-loaded into HANA), so the split survives deployment
    without shipping the whole dataset/ folder."""
    corpus_index = load_corpus_index()
    sample_ids = {p.id for p in load_sample_papers()}
    upload_ids = {p.id for p in get_store().uploaded_papers()}

    rows: list[PaperModel] = []
    for paper in _library_papers():
        entry = corpus_index.get(paper.id)
        if entry:
            split = entry.get("split") or "corpus"
            sub_area = entry.get("sub_area", "")
        elif paper.id in upload_ids:
            split, sub_area = "uploaded", ""
        elif paper.id in sample_ids:
            split, sub_area = "sample", ""
        else:
            split, sub_area = "", ""
        rows.append(PaperModel(**vars(paper), split=split, sub_area=sub_area))
    return rows


@app.get("/api/domains", response_model=list[str], dependencies=_admin_only)
def list_domains() -> list[str]:
    return _all_domains()


@app.post("/api/domains", response_model=list[str], dependencies=_admin_only)
def create_domain(request: CreateDomainRequest) -> list[str]:
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Domain name is required")
    if name.lower() not in {d.lower() for d in _all_domains()}:
        get_store().add_custom_domain(name)
    return _all_domains()


@app.delete("/api/domains/{name}", response_model=list[str], dependencies=_admin_only)
def delete_domain(name: str) -> list[str]:
    """Remove a custom (empty) domain. Domains still used by a paper are unaffected."""
    get_store().remove_custom_domain(name)
    return _all_domains()


@app.post("/api/papers", response_model=PaperModel, dependencies=_admin_only)
async def create_paper(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    domain: str = Form(...),
    authors: str = Form(""),
    year: str = Form(""),
    abstract: str = Form(""),
    limitations_text: str = Form(""),
    method_text: str = Form(""),
    file: UploadFile | None = File(None),
) -> PaperModel:
    """Curator-only: the 'Upload file' dialog. Store the paper (metadata + optional
    PDF) and retrain the search indexes in the background."""
    title = title.strip()
    domain = domain.strip() or "Uncategorised"
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    payload = b""
    pdf_text = ""
    if file is not None and file.filename:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        payload = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(payload)
            tmp_path = tmp.name
        from bridgescout.ingestion.pdf_loader import extract_text_from_pdf

        pdf_text = clean_text(extract_text_from_pdf(tmp_path))

    paper_id = _unique_paper_id(title)
    paper = Paper(
        id=paper_id,
        title=title,
        domain=domain,
        abstract=(abstract.strip() or pdf_text[:500]),
        authors=authors.strip(),
        year=int(year) if year.strip().isdigit() else None,
        limitations_text=(limitations_text.strip() or pdf_text),
        method_text=(method_text.strip() or abstract.strip() or pdf_text[:1000]),
        source="admin-upload",
    )

    get_store().add_paper(
        paper,
        payload or None,
        file.filename if (file and file.filename) else None,
        "application/pdf",
    )
    _schedule_retrain(background_tasks)
    return PaperModel(**vars(paper))


@app.get("/api/papers/{paper_id}/file", dependencies=_admin_only)
def get_paper_file(paper_id: str, download: bool = False) -> Response:
    """Curator-only: the paper's source document for the right-side iframe / download.

    Serves the stored PDF (admin upload, from HANA or the filesystem), then a
    collected-corpus PDF if one is on disk, otherwise a readable HTML rendering.
    """
    paper = _find_library_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"Unknown paper '{paper_id}'")

    safe_name = "".join(c for c in paper.title if c.isalnum() or c in " -_").strip() or paper_id
    disposition = "attachment" if download else "inline"

    stored = get_store().paper_file(paper_id)
    if stored is not None:
        return Response(
            content=stored.data,
            media_type=stored.content_type or "application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="{safe_name}.pdf"'},
        )

    corpus_pdf = corpus_pdf_path(paper_id)
    if corpus_pdf is not None and corpus_pdf.exists():
        return FileResponse(
            corpus_pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="{safe_name}.pdf"'},
        )

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{paper_id}.html"'
    return HTMLResponse(content=_paper_as_html(paper), headers=headers)


@app.post("/api/papers/upload", response_model=PaperModel, dependencies=_protected)
async def upload_paper(
    file: UploadFile = File(...),
    domain: str = Form("Unknown"),
) -> PaperModel:
    """Analyze-section upload: parse the PDF and return it for a one-off
    cross-domain analysis. It is NOT persisted and NOT added to training - that
    only happens through the curator's "Training papers -> Upload file"
    (POST /api/papers)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    payload = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(payload)
        tmp_path = tmp.name
    paper = load_pdf_as_paper(tmp_path, title=file.filename, domain=domain)
    return PaperModel(**vars(paper))


@app.delete("/api/papers/{paper_id}", dependencies=_admin_only)
def delete_paper(paper_id: str) -> dict:
    """Curator-only: remove a paper from the library. Uploaded papers (and their
    stored file) are deleted; a seed / corpus paper is hidden via a deletion row.
    No re-embed: the paper is filtered out of search results from now on and drops
    from the index at the next full rebuild."""
    if _find_library_paper(paper_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown paper '{paper_id}'")

    store = get_store()
    if not store.remove_paper(paper_id):
        store.add_deleted_id(paper_id)

    return {"deleted": paper_id}


@app.get("/api/index/status", response_model=IndexStatus, dependencies=_protected)
def index_status() -> IndexStatus:
    return IndexStatus(**{**_index_state, "papers": len(_library_papers())})


@app.post("/api/ask", response_model=AskResponse, dependencies=_protected)
def ask(request: AskRequest) -> AskResponse:
    """End-user question answering: return passages from library papers that
    answer the question, or nothing when the library has no relevant information."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="A question is required")

    live_ids = {p.id for p in _library_papers()}
    hits = _content_index.search(question, top_k=max(1, min(request.top_k, 10)) * 3)
    strong: list[AskMatch] = []
    for meta, score in hits:
        if score < _QA_MIN_SCORE or meta["paper_id"] not in live_ids:
            continue
        strong.append(
            AskMatch(
                paper_id=meta["paper_id"],
                paper_title=meta["paper_title"],
                domain=meta["domain"],
                snippet=meta["snippet"],
                score=round(score, 4),
            )
        )
        if len(strong) >= min(request.top_k, 10):
            break
    return AskResponse(question=question, answer_found=bool(strong), matches=strong)


@app.post("/api/analyze", response_model=AnalyzeResponse, dependencies=_protected)
def analyze_paper(request: AnalyzeRequest) -> AnalyzeResponse:
    paper = _to_paper(request.paper)
    gaps = extract_gaps_for_paper(paper, _llm_client)
    live_ids = {p.id for p in _library_papers()}

    gap_results: list[GapResult] = []
    for index, gap in enumerate(gaps):
        neutral_gap = normalize_gap(gap, paper.domain, _llm_client)
        raw_candidates = search_cross_domain(
            _vector_store, neutral_gap, paper.domain, paper.id,
            top_k=TOP_K_RESULTS, allowed_ids=live_ids,
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
