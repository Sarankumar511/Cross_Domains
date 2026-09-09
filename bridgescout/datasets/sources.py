"""Fetch research-paper metadata from PubMed (NCBI E-utilities) and arXiv.

Both APIs are public and keyless. PubMed abstracts are richer for clinical
disease topics; arXiv adds computational / q-bio work on the same conditions.
Every network call is wrapped so one bad response never aborts a whole build.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ARXIV_API_URL = "https://export.arxiv.org/api/query"
OPENALEX_API_URL = "https://api.openalex.org/works"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

USER_AGENT = "BridgeScout-dataset-builder/0.1 (research prototype; +https://github.com/)"
OPENALEX_MAILTO = "bridgescout-dataset@example.com"  # OpenAlex "polite pool" contact
_MAX_AUTHORS = 8


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def pubmed_delay(api_key: str = "") -> float:
    """NCBI allows 3 req/s without a key, 10 req/s with one."""
    return 0.11 if api_key else 0.34


# --------------------------------------------------------------------------- #
# PubMed
# --------------------------------------------------------------------------- #
def fetch_pubmed(
    sub_area: str,
    query: str,
    max_results: int,
    session: requests.Session | None = None,
    api_key: str = "",
) -> list[dict]:
    session = session or make_session()
    ids = _pubmed_esearch(query, max_results, session, api_key)
    if not ids:
        return []
    time.sleep(pubmed_delay(api_key))
    xml_text = _pubmed_efetch(ids, session, api_key)
    if not xml_text:
        return []
    return _parse_pubmed_xml(xml_text, sub_area)


def _pubmed_esearch(query: str, retmax: int, session: requests.Session, api_key: str) -> list[str]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "sort": "relevance",
    }
    if api_key:
        params["api_key"] = api_key
    try:
        resp = session.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("esearchresult", {}).get("idlist", [])
    except (requests.RequestException, ValueError) as exc:
        print(f"  [pubmed] esearch failed for {query!r}: {exc}")
        return []


def _pubmed_efetch(pmids: list[str], session: requests.Session, api_key: str) -> str:
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    if api_key:
        params["api_key"] = api_key
    try:
        resp = session.get(f"{EUTILS_BASE}/efetch.fcgi", params=params, timeout=60)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        print(f"  [pubmed] efetch failed ({len(pmids)} ids): {exc}")
        return ""


def _parse_pubmed_xml(xml_text: str, sub_area: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        print(f"  [pubmed] XML parse error: {exc}")
        return []

    records: list[dict] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID", default="").strip()
        title = _node_text(article, ".//ArticleTitle")
        abstract = _join_abstract(article)
        if not pmid or not title or not abstract:
            continue

        doi = ""
        pmcid = ""
        for aid in article.findall(".//ArticleId"):
            id_type = aid.get("IdType", "")
            if id_type == "doi":
                doi = (aid.text or "").strip()
            elif id_type == "pmc":
                pmcid = (aid.text or "").strip()

        records.append(
            {
                "id": f"pubmed-{pmid}",
                "source": "pubmed",
                "sub_area": sub_area,
                "title": title,
                "abstract": abstract,
                "authors": _pubmed_authors(article),
                "year": _pubmed_year(article),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "doi": doi,
                "pmcid": pmcid,
            }
        )
    return records


def _join_abstract(article: ET.Element) -> str:
    parts: list[str] = []
    for node in article.findall(".//Abstract/AbstractText"):
        text = "".join(node.itertext()).strip()
        if not text:
            continue
        label = node.get("Label")
        parts.append(f"{label}: {text}" if label else text)
    return _clean(" ".join(parts))


def _pubmed_authors(article: ET.Element) -> str:
    names: list[str] = []
    for author in article.findall(".//AuthorList/Author"):
        last = author.findtext("LastName", default="").strip()
        initials = author.findtext("Initials", default="").strip()
        collective = author.findtext("CollectiveName", default="").strip()
        if last:
            names.append(f"{initials} {last}".strip())
        elif collective:
            names.append(collective)
        if len(names) >= _MAX_AUTHORS:
            names.append("et al.")
            break
    return ", ".join(names)


def _pubmed_year(article: ET.Element) -> int | None:
    year = article.findtext(".//JournalIssue/PubDate/Year", default="").strip()
    if year.isdigit():
        return int(year)
    medline_date = article.findtext(".//JournalIssue/PubDate/MedlineDate", default="").strip()
    for token in medline_date.replace("-", " ").split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


# --------------------------------------------------------------------------- #
# arXiv
# --------------------------------------------------------------------------- #
def fetch_arxiv(
    sub_area: str,
    query: str,
    max_results: int,
    session: requests.Session | None = None,
    api_key: str = "",  # unused; kept for a uniform fetcher signature
) -> list[dict]:
    session = session or make_session()
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    try:
        resp = session.get(ARXIV_API_URL, params=params, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [arxiv] query failed for {query!r}: {exc}")
        return []
    return _parse_arxiv_xml(resp.text, sub_area)


def _parse_arxiv_xml(xml_text: str, sub_area: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        print(f"  [arxiv] XML parse error: {exc}")
        return []

    records: list[dict] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        raw_id = _node_text(entry, "atom:id", ATOM_NS)
        title = _node_text(entry, "atom:title", ATOM_NS)
        summary = _node_text(entry, "atom:summary", ATOM_NS)
        if not raw_id or not title or not summary:
            continue

        arxiv_id = raw_id.rsplit("/", 1)[-1]
        published = _node_text(entry, "atom:published", ATOM_NS)
        year = int(published[:4]) if published[:4].isdigit() else None

        authors = [
            _node_text(a, "atom:name", ATOM_NS)
            for a in entry.findall("atom:author", ATOM_NS)
        ]
        authors = [a for a in authors if a]
        if len(authors) > _MAX_AUTHORS:
            authors = authors[:_MAX_AUTHORS] + ["et al."]

        doi = _node_text(entry, "arxiv:doi", ATOM_NS)

        records.append(
            {
                "id": f"arxiv-{arxiv_id}",
                "source": "arxiv",
                "sub_area": sub_area,
                "title": title,
                "abstract": summary,
                "authors": ", ".join(authors),
                "year": year,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "doi": doi,
                "arxiv_id": arxiv_id,
            }
        )
    return records


# --------------------------------------------------------------------------- #
# OpenAlex  (keyless; used as the second source for non-medical domains)
# --------------------------------------------------------------------------- #
def fetch_openalex(
    sub_area: str,
    query: str,
    max_results: int,
    session: requests.Session | None = None,
    api_key: str = "",  # unused; kept for a uniform fetcher signature
) -> list[dict]:
    session = session or make_session()
    params = {
        "search": query,
        "filter": "has_abstract:true,type:article,language:en",
        "per-page": min(max(max_results, 1), 200),
        "select": "id,doi,title,display_name,publication_year,authorships,"
        "abstract_inverted_index,best_oa_location,primary_location,open_access",
        "mailto": OPENALEX_MAILTO,
    }
    for attempt in range(4):
        try:
            resp = session.get(OPENALEX_API_URL, params=params, timeout=40)
        except requests.RequestException as exc:
            print(f"  [openalex] request failed for {query!r}: {exc}")
            return []
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"  [openalex] 429 rate-limited, waiting {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            print(f"  [openalex] HTTP {resp.status_code} for {query!r}")
            return []
        try:
            results = resp.json().get("results", []) or []
        except ValueError:
            return []
        return _parse_openalex(results, sub_area)
    return []


def _parse_openalex(results: list[dict], sub_area: str) -> list[dict]:
    records: list[dict] = []
    for work in results:
        title = _clean(work.get("title") or work.get("display_name") or "")
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        oa_id = (work.get("id") or "").rsplit("/", 1)[-1]
        if not title or not abstract or not oa_id:
            continue

        doi = (work.get("doi") or "").replace("https://doi.org/", "").strip()
        authors = [
            _clean((a.get("author") or {}).get("display_name") or "")
            for a in work.get("authorships") or []
        ]
        authors = [a for a in authors if a]
        if len(authors) > _MAX_AUTHORS:
            authors = authors[:_MAX_AUTHORS] + ["et al."]

        records.append(
            {
                "id": f"openalex-{oa_id}",
                "source": "openalex",
                "sub_area": sub_area,
                "title": title,
                "abstract": abstract,
                "authors": ", ".join(authors),
                "year": work.get("publication_year"),
                "url": work.get("id") or "",
                "doi": doi,
                "oa_pdf_url": _openalex_pdf_url(work),
            }
        )
    return records


def _openalex_pdf_url(work: dict) -> str:
    for key in ("best_oa_location", "primary_location"):
        location = work.get(key) or {}
        pdf_url = location.get("pdf_url")
        if pdf_url:
            return pdf_url
    return (work.get("open_access") or {}).get("oa_url") or ""


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            positioned.append((pos, word))
    positioned.sort()
    return _clean(" ".join(word for _, word in positioned))


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _node_text(node: ET.Element, path: str, ns: dict | None = None) -> str:
    found = node.find(path, ns) if ns else node.find(path)
    if found is None:
        return ""
    return _clean("".join(found.itertext()))


def _clean(text: str) -> str:
    return " ".join((text or "").split())
