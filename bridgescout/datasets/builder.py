"""Generic corpus builder: fetch -> dedupe -> PDFs -> stratified 80/20 split.

Domain-agnostic. A domain is just a name plus a per-sub-area map of source
queries; see :mod:`bridgescout.datasets.registry` for the concrete specs and
:func:`bridgescout.datasets.disease.build_disease_dataset` for a thin wrapper.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from bridgescout.datasets.pdfs import DEFAULT_MAX_PDF_BYTES, download_pdfs
from bridgescout.datasets.schema import DatasetRecord
from bridgescout.datasets.sources import (
    fetch_arxiv,
    fetch_openalex,
    fetch_pubmed,
    make_session,
    pubmed_delay,
)
from bridgescout.datasets.split import stratified_split

# name -> (fetcher, seconds to pause after each call to be polite)
SOURCE_FETCHERS = {
    "pubmed": (fetch_pubmed, 0.34),
    "arxiv": (fetch_arxiv, 3.0),
    "openalex": (fetch_openalex, 1.0),
}


def build_domain_dataset(
    domain: str,
    area_queries: dict[str, dict[str, str]],
    out_dir: Path,
    source_names: tuple[str, ...] = ("arxiv", "openalex"),
    per_area: int = 50,
    source_shares: dict[str, float] | None = None,
    test_ratio: float = 0.2,
    seed: int = 42,
    download_pdf: bool = True,
    pdf_skip_sources: tuple[str, ...] = (),
    areas: list[str] | None = None,
    api_key: str = "",
    max_pdf_bytes: int = DEFAULT_MAX_PDF_BYTES,
) -> dict:
    unknown_sources = [s for s in source_names if s not in SOURCE_FETCHERS]
    if unknown_sources:
        raise ValueError(f"Unknown source(s): {unknown_sources}. Known: {list(SOURCE_FETCHERS)}")

    out_dir = Path(out_dir)
    raw_dir = out_dir / "raw"
    pdfs_dir = out_dir / "pdfs"
    raw_dir.mkdir(parents=True, exist_ok=True)

    selected = _select_areas(area_queries, areas)
    quotas = _source_quotas(source_names, per_area, source_shares)
    session = make_session()

    raw_rows: list[dict] = []
    per_area_raw: dict[str, dict[str, int]] = {}
    for area in selected:
        per_area_raw[area] = {}
        counts = []
        for source in source_names:
            query = area_queries[area].get(source)
            if not query or quotas[source] <= 0:
                per_area_raw[area][source] = 0
                continue
            fetcher, pause = SOURCE_FETCHERS[source]
            rows = fetcher(area, query, quotas[source], session, api_key)
            per_area_raw[area][source] = len(rows)
            raw_rows.extend(rows)
            counts.append(f"{len(rows)} {source}")
            time.sleep(pubmed_delay(api_key) if source == "pubmed" else pause)
        print(f"[{domain}/{area}] {' + '.join(counts) or 'nothing fetched'}")

    _write_json(raw_dir / "raw.json", raw_rows)

    records = _dedupe([DatasetRecord(domain=domain, **row) for row in raw_rows])
    print(f"[{domain}] {len(records)} records after de-duplication (from {len(raw_rows)} raw)")

    pdf_stats: dict = {}
    if download_pdf and records:
        print(f"[{domain}] downloading open-access PDFs -> {pdfs_dir}")
        pdf_stats = download_pdfs(
            records, pdfs_dir, out_dir, session, max_pdf_bytes, pdf_skip_sources
        )
        print(f"[{domain}] PDF results: {pdf_stats}")

    train, test = stratified_split(records, test_ratio=test_ratio, seed=seed)
    _write_json(out_dir / "all_papers.json", [r.to_dict() for r in records])
    _write_json(out_dir / "train.json", [r.to_dict() for r in train])
    _write_json(out_dir / "test.json", [r.to_dict() for r in test])

    manifest = _build_manifest(
        domain, selected, source_names, per_area_raw, records, train, test,
        pdf_stats, per_area, quotas, test_ratio, seed,
    )
    _write_json(out_dir / "split_manifest.json", manifest)
    _write_readme(out_dir, manifest)
    print(f"[{domain}] wrote {out_dir} ({len(train)} train / {len(test)} test)")
    return manifest


def _select_areas(area_queries: dict, areas: list[str] | None) -> list[str]:
    if not areas:
        return list(area_queries)
    unknown = [a for a in areas if a not in area_queries]
    if unknown:
        raise ValueError(f"Unknown area(s): {unknown}. Known: {list(area_queries)}")
    return areas


def _source_quotas(
    source_names: tuple[str, ...], per_area: int, source_shares: dict[str, float] | None
) -> dict[str, int]:
    if source_shares is None:
        share = 1.0 / len(source_names)
        source_shares = {name: share for name in source_names}
    quotas = {name: max(0, round(per_area * source_shares.get(name, 0.0))) for name in source_names}
    # Hand any rounding remainder to the first source so totals land on per_area.
    drift = per_area - sum(quotas.values())
    if drift and source_names:
        quotas[source_names[0]] = max(0, quotas[source_names[0]] + drift)
    return quotas


def _dedupe(records: list[DatasetRecord]) -> list[DatasetRecord]:
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    seen_dois: set[str] = set()
    kept: list[DatasetRecord] = []
    for record in records:
        title_key = "".join(ch for ch in record.title.lower() if ch.isalnum())
        doi_key = record.doi.lower().strip()
        if record.id in seen_ids or title_key in seen_titles:
            continue
        if doi_key and doi_key in seen_dois:
            continue
        seen_ids.add(record.id)
        seen_titles.add(title_key)
        if doi_key:
            seen_dois.add(doi_key)
        kept.append(record)
    return kept


def _area_counts(records: list[DatasetRecord]) -> dict[str, int]:
    out: dict[str, int] = {}
    for record in records:
        out[record.sub_area] = out.get(record.sub_area, 0) + 1
    return out


def _build_manifest(
    domain, selected, source_names, per_area_raw, records, train, test,
    pdf_stats, per_area, quotas, test_ratio, seed,
) -> dict:
    with_pdf = sum(1 for r in records if r.pdf_path)
    by_source: dict[str, int] = {}
    for record in records:
        by_source[record.source] = by_source.get(record.source, 0) + 1
    return {
        "domain": domain,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "params": {
            "per_area": per_area,
            "source_quotas": quotas,
            "sources": list(source_names),
            "test_ratio": test_ratio,
            "seed": seed,
            "areas": selected,
        },
        "totals": {
            "records": len(records),
            "train": len(train),
            "test": len(test),
            "with_pdf": with_pdf,
            "pdf_coverage": round(with_pdf / len(records), 3) if records else 0.0,
        },
        "by_source": by_source,
        "raw_fetched_by_area": per_area_raw,
        "records_by_area": _area_counts(records),
        "train_by_area": _area_counts(train),
        "test_by_area": _area_counts(test),
        "pdf_stats": pdf_stats,
    }


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _write_readme(out_dir: Path, manifest: dict) -> None:
    domain = manifest["domain"]
    totals = manifest["totals"]
    source_line = ", ".join(f"{name} ({count})" for name, count in sorted(manifest["by_source"].items()))
    lines = [
        f"# {domain} dataset",
        "",
        f"Generated: {manifest['generated_utc']}",
        "",
        f"Real research papers from **{', '.join(manifest['params']['sources'])}**, spanning "
        f"{len(manifest['params']['areas'])} sub-areas, with a reproducible stratified "
        f"{int((1 - manifest['params']['test_ratio']) * 100)}/"
        f"{int(manifest['params']['test_ratio'] * 100)} train/test split "
        f"(seed {manifest['params']['seed']}).",
        "",
        "## Contents",
        "",
        "| File | What |",
        "|---|---|",
        "| `all_papers.json` | Every de-duplicated record |",
        "| `train.json` / `test.json` | The split, stratified by sub-area |",
        "| `split_manifest.json` | Counts, parameters, seed, PDF coverage |",
        "| `pdfs/<id>.pdf` | Open-access full text where reachable |",
        "| `raw/raw.json` | Unprocessed fetch output |",
        "",
        "## Totals",
        "",
        f"- Records: **{totals['records']}** ({source_line})",
        f"- Train / Test: **{totals['train']} / {totals['test']}**",
        f"- With PDF: **{totals['with_pdf']}** ({totals['pdf_coverage'] * 100:.0f}% coverage)",
        "",
        "## Records by sub-area (train / test)",
        "",
        "| Sub-area | Total | Train | Test |",
        "|---|--:|--:|--:|",
    ]
    for area in sorted(manifest["records_by_area"]):
        lines.append(
            f"| {area} | {manifest['records_by_area'][area]} | "
            f"{manifest['train_by_area'].get(area, 0)} | {manifest['test_by_area'].get(area, 0)} |"
        )
    lines += [
        "",
        "Each record matches `bridgescout.ingestion.preprocessing.Paper` "
        "(`limitations_text` / `method_text` mirror the abstract), plus "
        "`sub_area`, `url`, `doi`, `pdf_path`, `pdf_source`, `split`.",
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
