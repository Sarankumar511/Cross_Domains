"""Best-effort open-access PDF download for collected records.

- arXiv: every paper has a PDF at ``arxiv.org/pdf/<id>`` (near 100% coverage).
- OpenAlex: use the ``pdf_url`` / ``oa_url`` it reports; these point at arbitrary
  publisher or repository hosts, so success is hit-or-miss.
- PubMed: only PMC Open Access papers have a fetchable PDF, via Europe PMC's
  render endpoint. Records with no reachable PDF keep ``pdf_path == ""``.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

from bridgescout.datasets.schema import DatasetRecord

PDF_MAGIC = b"%PDF-"
MIN_PDF_BYTES = 2048
DEFAULT_MAX_PDF_BYTES = 40 * 1024 * 1024
_DOWNLOAD_PAUSE = 0.3
# (connect, read) seconds. Publisher / PMC hosts that block scripts tend to hang,
# so keep these tight — arXiv is the only route we actually rely on.
_TIMEOUT = (8, 40)
# Only arXiv is worth retrying; PMC render is persistently flaky and OA URLs
# point at arbitrary hosts, so one clean shot each.
_RETRIES_BY_SOURCE = {"arxiv": 1, "pmc-oa": 0, "oa-url": 0}
# Stop hammering a route once it has failed this many times in a row.
_CIRCUIT_BREAK_AFTER = 15


def download_pdfs(
    records: list[DatasetRecord],
    pdfs_dir: Path,
    domain_dir: Path,
    session: requests.Session | None = None,
    max_bytes: int = DEFAULT_MAX_PDF_BYTES,
    skip_sources: tuple[str, ...] = (),
) -> dict:
    """Try to fetch a PDF for every record; mutate records in place.

    ``skip_sources`` names PDF routes to not even attempt (e.g. ``("oa-url",
    "pmc-oa")`` to keep only the fast, reliable arXiv route).

    Returns a small stats dict (attempted / downloaded / skipped counts).
    """
    session = session or requests.Session()
    pdfs_dir.mkdir(parents=True, exist_ok=True)
    skip = set(skip_sources)

    stats = {"downloaded": 0, "failed": 0, "no_source": 0, "skipped_dead_route": 0, "by_source": {}}
    consecutive_fail: dict[str, int] = {}
    dead_routes: set[str] = set()
    processed = 0
    for record in records:
        url, pdf_source = _resolve(record)
        if not url or pdf_source in skip:
            stats["no_source"] += 1
            continue

        dest = pdfs_dir / f"{record.id}.pdf"
        cached = dest.exists() and dest.stat().st_size >= MIN_PDF_BYTES

        if not cached and pdf_source in dead_routes:
            stats["skipped_dead_route"] += 1
            stats["failed"] += 1
            continue

        processed += 1
        ok = cached or _download(
            session, url, dest, max_bytes, retries=_RETRIES_BY_SOURCE.get(pdf_source, 0)
        )
        if ok:
            record.pdf_path = dest.relative_to(domain_dir).as_posix()
            record.pdf_source = pdf_source
            stats["downloaded"] += 1
            stats["by_source"][pdf_source] = stats["by_source"].get(pdf_source, 0) + 1
            consecutive_fail[pdf_source] = 0
        else:
            stats["failed"] += 1
            consecutive_fail[pdf_source] = consecutive_fail.get(pdf_source, 0) + 1
            if consecutive_fail[pdf_source] >= _CIRCUIT_BREAK_AFTER:
                dead_routes.add(pdf_source)
                print(f"  [pdf] giving up on '{pdf_source}' after "
                      f"{_CIRCUIT_BREAK_AFTER} consecutive failures")

        if processed % 25 == 0:
            print(f"  [pdf] {processed} tried "
                  f"(downloaded {stats['downloaded']}, failed {stats['failed']})")
        if not cached:
            time.sleep(_DOWNLOAD_PAUSE)

    return stats


def _resolve(record: DatasetRecord) -> tuple[str, str]:
    if record.source == "arxiv" and record.arxiv_id:
        return f"https://arxiv.org/pdf/{record.arxiv_id}", "arxiv"
    if record.source == "pubmed" and record.pmcid:
        pmcid = record.pmcid if record.pmcid.upper().startswith("PMC") else f"PMC{record.pmcid}"
        return (
            f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf",
            "pmc-oa",
        )
    if record.oa_pdf_url:
        return record.oa_pdf_url, "oa-url"
    return "", ""


def _download(session: requests.Session, url: str, dest: Path, max_bytes: int, retries: int = 1) -> bool:
    for attempt in range(retries + 1):
        try:
            with session.get(url, timeout=_TIMEOUT, stream=True, allow_redirects=True) as resp:
                if resp.status_code >= 500 and attempt < retries:
                    time.sleep(3.0)
                    continue
                if resp.status_code != 200:
                    return False
                if "html" in resp.headers.get("Content-Type", "").lower():
                    return False

                chunks: list[bytes] = []
                total = 0
                for chunk in resp.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > max_bytes:
                        return False

            blob = b"".join(chunks)
            if len(blob) < MIN_PDF_BYTES or not blob.lstrip()[:8].startswith(PDF_MAGIC):
                return False
            dest.write_bytes(blob)
            return True
        except (requests.RequestException, OSError) as exc:
            if attempt < retries:
                time.sleep(3.0)
                continue
            print(f"  [pdf] failed {url}: {exc}")
            return False
    return False
