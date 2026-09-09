"""Load the collected train/test corpus into the HANA PAPERS table.

The deployed backend excludes ``dataset/`` from its droplet, so on Cloud Foundry
``load_corpus_papers()`` finds nothing and the curator library is empty. This
script pushes the corpus straight into the ``bridgescout-hdi-container`` PAPERS
table so the running app serves it.

Two passes (run metadata first, then --pdfs-only):

    python scripts/load_library_hana.py --key sk.json                 # ~2180 metadata rows
    python scripts/load_library_hana.py --key sk.json --pdfs-only     # fill FILE_DATA from dataset/*/pdfs/

``--pdfs-only`` UPDATEs FILE_DATA for rows that have a local PDF and skips rows
already carrying one, so it is safe to re-run after a timeout.

Credentials come from, in order:
  1. --key <file>   a `cf service-key <hdi-container> <name>` JSON dump
  2. VCAP_SERVICES  (inside a bound CF container / `cf ssh`)
  3. HANA_HOST / HANA_PORT / HANA_USER / HANA_PASSWORD / HANA_SCHEMA env vars

    cf create-service-key bridgescout-hdi-container loader
    cf service-key bridgescout-hdi-container loader > sk.json    # keep only the JSON
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridgescout.datasets.library import load_corpus_papers
from bridgescout.storage.base import PAPER_FIELDS

_TABLE = "PAPERS"


# --------------------------------------------------------------------------- #
# credentials
# --------------------------------------------------------------------------- #
def _creds_from_key_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    brace = text.find("{")  # `cf service-key` prints a header line before the JSON
    if brace > 0:
        text = text[brace:]
    data = json.loads(text)
    return data.get("credentials", data)


def _creds_from_vcap() -> dict | None:
    raw = os.getenv("VCAP_SERVICES")
    if not raw:
        return None
    services = json.loads(raw)
    for key in ("hana", "hana-cloud", "hanatrial", "managed-hana"):
        for binding in services.get(key, []):
            creds = binding.get("credentials") or {}
            if creds.get("host") and creds.get("schema") and creds.get("user"):
                return creds
    return None


def _creds_from_env() -> dict | None:
    host = os.getenv("HANA_HOST")
    if not host:
        return None
    return {
        "host": host,
        "port": os.getenv("HANA_PORT", "443"),
        "user": os.getenv("HANA_USER", ""),
        "password": os.getenv("HANA_PASSWORD", ""),
        "schema": os.getenv("HANA_SCHEMA", ""),
    }


def _resolve_creds(args) -> dict:
    if args.key:
        return _creds_from_key_file(Path(args.key))
    for fn in (_creds_from_vcap, _creds_from_env):
        creds = fn()
        if creds:
            return creds
    raise SystemExit(
        "No HANA credentials. Pass --key <service-key.json>, run inside a bound "
        "container, or set HANA_HOST/HANA_USER/HANA_PASSWORD/HANA_SCHEMA."
    )


def _connect(creds: dict):
    from hdbcli import dbapi

    kwargs = dict(
        address=creds["host"],
        port=int(creds["port"]),
        user=creds["user"],
        password=creds["password"],
        currentSchema=creds["schema"],
        encrypt=True,
        autocommit=False,
    )
    cert = creds.get("certificate")
    if cert:
        kwargs["sslValidateCertificate"] = True
        kwargs["sslTrustStore"] = cert
    else:
        kwargs["sslValidateCertificate"] = False
    return dbapi.connect(**kwargs)


# --------------------------------------------------------------------------- #
# corpus helpers
# --------------------------------------------------------------------------- #
def _unique_corpus() -> list[tuple]:
    """(paper, meta) with duplicate ids (same paper matched by two domains) dropped."""
    seen: set[str] = set()
    out = []
    for paper, meta in load_corpus_papers():
        if not paper.id or paper.id in seen:
            continue
        seen.add(paper.id)
        out.append((paper, meta))
    return out


def _local_pdf(meta: dict, max_bytes: int) -> Path | None:
    path = meta.get("pdf_path") or ""
    if not path:
        return None
    p = Path(path)
    if not p.exists() or p.stat().st_size > max_bytes or p.stat().st_size < 1024:
        return None
    return p


# --------------------------------------------------------------------------- #
# passes
# --------------------------------------------------------------------------- #
def _load_metadata(cur, conn, corpus, batch: int) -> int:
    # FILE_DATA is deliberately NOT in the column list: UPSERT ... WITH PRIMARY
    # KEY only touches listed columns, so a PDF loaded by --pdfs-only survives a
    # re-run of the metadata pass. CREATED_AT is only set on first insert.
    cols = [c.upper() for c in PAPER_FIELDS] + ["CREATED_AT"]
    col_sql = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(["?"] * len(PAPER_FIELDS) + ["CURRENT_TIMESTAMP"])
    upsert = f'UPSERT "{_TABLE}" ({col_sql}) VALUES ({placeholders}) WITH PRIMARY KEY'

    rows, loaded = [], 0
    started = time.time()
    for paper, _meta in corpus:
        rows.append([getattr(paper, c, None) for c in PAPER_FIELDS])
        loaded += 1
        if len(rows) >= batch:
            cur.executemany(upsert, rows)
            conn.commit()
            rows = []
            print(f"  metadata: {loaded} rows ({time.time() - started:.0f}s)")
    if rows:
        cur.executemany(upsert, rows)
        conn.commit()
    return loaded


def _load_pdfs(cur, conn, corpus, max_bytes: int, batch: int, force: bool) -> tuple[int, int, int]:
    have: set[str] = set()
    if not force:
        cur.execute(f'SELECT "ID" FROM "{_TABLE}" WHERE "FILE_DATA" IS NOT NULL')
        have = {r[0] for r in cur.fetchall()}
        print(f"  {len(have)} rows already have a PDF - skipping those")

    sql = f'UPDATE "{_TABLE}" SET "FILE_DATA" = ?, "FILE_NAME" = ?, "CONTENT_TYPE" = ? WHERE "ID" = ?'
    rows: list[list] = []
    done = skipped = missing = 0
    sent_bytes = 0
    started = time.time()

    def flush() -> None:
        nonlocal rows
        if rows:
            cur.executemany(sql, rows)
            conn.commit()
            rows = []

    for paper, meta in corpus:
        if paper.id in have:
            skipped += 1
            continue
        pdf = _local_pdf(meta, max_bytes)
        if pdf is None:
            missing += 1
            continue
        data = pdf.read_bytes()
        rows.append([data, pdf.name, "application/pdf", paper.id])
        sent_bytes += len(data)
        done += 1
        if len(rows) >= batch:
            flush()
            print(f"  pdfs: {done} loaded, {sent_bytes / 1e6:.0f} MB ({time.time() - started:.0f}s)")
    flush()
    return done, skipped, missing


# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--key", help="Path to a `cf service-key` JSON dump for the HDI container")
    parser.add_argument("--pdfs-only", action="store_true", help="Only fill FILE_DATA from dataset/*/pdfs/ (targeted UPDATE, resumable)")
    parser.add_argument("--with-pdfs", action="store_true", help="Metadata pass AND PDFs in one go")
    parser.add_argument("--max-pdf-mb", type=float, default=5.0, help="Skip PDFs larger than this (default 5)")
    parser.add_argument("--batch", type=int, default=200, help="Metadata rows per commit (default 200)")
    parser.add_argument("--pdf-batch", type=int, default=15, help="PDF rows per commit (default 15)")
    parser.add_argument("--force", action="store_true", help="Re-send PDFs even for rows that already have one")
    parser.add_argument("--truncate", action="store_true", help="DELETE all PAPERS rows first")
    parser.add_argument("--dry-run", action="store_true", help="Report what would load; touch no DB")
    args = parser.parse_args()

    corpus = _unique_corpus()
    print(f"unique corpus papers on disk: {len(corpus)}")
    if not corpus:
        raise SystemExit("dataset/<Domain>/{train,test}.json produced no papers - nothing to load.")

    max_bytes = int(args.max_pdf_mb * 1024 * 1024)

    if args.dry_run:
        with_pdf = [(p, m) for p, m in corpus if _local_pdf(m, max_bytes)]
        total = sum(_local_pdf(m, max_bytes).stat().st_size for _, m in with_pdf)
        print(f"PDFs <= {args.max_pdf_mb} MB: {len(with_pdf)} files, {total / 1e6:.0f} MB")
        return

    conn = _connect(_resolve_creds(args))
    cur = conn.cursor()
    print("connected.")

    if args.truncate:
        cur.execute(f'DELETE FROM "{_TABLE}"')
        conn.commit()
        print(f'truncated "{_TABLE}"')

    if not args.pdfs_only:
        loaded = _load_metadata(cur, conn, corpus, args.batch)
        print(f"metadata: {loaded} rows upserted.")

    if args.pdfs_only or args.with_pdfs:
        done, skipped, missing = _load_pdfs(cur, conn, corpus, max_bytes, args.pdf_batch, args.force)
        print(f"pdfs: {done} loaded, {skipped} already had one, {missing} have no local PDF <= {args.max_pdf_mb} MB.")

    cur.execute(f'SELECT COUNT(*), COUNT("FILE_DATA") FROM "{_TABLE}"')
    total, with_file = cur.fetchone()
    cur.close()
    conn.close()
    print(f"\nPAPERS now holds {total} rows, {with_file} with a PDF.")


if __name__ == "__main__":
    main()
