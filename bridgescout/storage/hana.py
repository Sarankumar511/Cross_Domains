"""HANA-backed library store, used when a HANA HDI container is bound on SAP BTP.

Tables are created design-time by the HDI container in ``db/src`` and deployed by
``bridgescout-db``; this class only does runtime DML against them, through the
container's runtime technical user (``credentials.user`` / ``.password`` with
``currentSchema = credentials.schema``).
"""

from __future__ import annotations

import threading

from bridgescout.ingestion.preprocessing import Paper
from bridgescout.storage.base import (
    PAPER_FIELDS,
    LibraryStore,
    StoredFile,
    paper_from_record,
)

_PAPERS = "PAPERS"
_DOMAINS = "DOMAINS"
_DELETED = "DELETED_PAPERS"


def _as_bytes(value) -> bytes:
    if value is None:
        return b""
    if hasattr(value, "read"):  # LOB handle
        return value.read()
    return bytes(value)


class HanaLibraryStore(LibraryStore):
    def __init__(self, credentials: dict) -> None:
        self._creds = credentials
        self._lock = threading.Lock()
        self._conn = None
        # In-process read caches. Free-tier HANA is slow and the library is read
        # on nearly every request (list, domains, index sync), so a full
        # SELECT * FROM PAPERS on each call made admin endpoints time out. These
        # are invalidated by this process's own writes; a second instance would
        # not see them, but the backend runs a single instance.
        self._papers_cache: list[Paper] | None = None
        self._deleted_cache: set[str] | None = None
        self._domains_cache: list[str] | None = None
        # Fail fast so the factory can fall back if the container isn't deployed yet.
        with self._cursor() as cur:
            cur.execute(f'SELECT 1 FROM "{_PAPERS}" WHERE 1 = 0')

    def _invalidate(self, *, papers: bool = False, deleted: bool = False, domains: bool = False) -> None:
        if papers:
            self._papers_cache = None
        if deleted:
            self._deleted_cache = None
        if domains:
            self._domains_cache = None

    # -- connection ------------------------------------------------------
    def _connect(self):
        from hdbcli import dbapi

        creds = self._creds
        kwargs = dict(
            address=creds["host"],
            port=int(creds["port"]),
            user=creds["user"],
            password=creds["password"],
            currentSchema=creds["schema"],
            encrypt=True,
            autocommit=True,
        )
        certificate = creds.get("certificate")
        if certificate:
            kwargs["sslValidateCertificate"] = True
            kwargs["sslTrustStore"] = certificate
        else:
            kwargs["sslValidateCertificate"] = False
        return dbapi.connect(**kwargs)

    class _CursorCtx:
        def __init__(self, store: "HanaLibraryStore") -> None:
            self._store = store

        def __enter__(self):
            self._store._lock.acquire()
            try:
                if self._store._conn is None or not self._store._conn.isconnected():
                    self._store._conn = self._store._connect()
                self._cur = self._store._conn.cursor()
                return self._cur
            except Exception:
                self._store._lock.release()
                raise

        def __exit__(self, *exc):
            try:
                self._cur.close()
            finally:
                self._store._lock.release()

    def _cursor(self) -> "HanaLibraryStore._CursorCtx":
        return HanaLibraryStore._CursorCtx(self)

    # -- uploaded papers ----------------------------------------------
    def uploaded_papers(self) -> list[Paper]:
        if self._papers_cache is not None:
            return self._papers_cache
        cols = ", ".join(f'"{c.upper()}"' for c in PAPER_FIELDS)
        with self._cursor() as cur:
            cur.execute(f'SELECT {cols} FROM "{_PAPERS}" ORDER BY "CREATED_AT"')
            rows = cur.fetchall()
        papers = []
        for row in rows:
            record = dict(zip(PAPER_FIELDS, row))
            papers.append(paper_from_record(record))
        self._papers_cache = papers
        return papers

    def add_paper(self, paper, file_bytes, file_name, content_type) -> None:
        cols = [c.upper() for c in PAPER_FIELDS] + [
            "FILE_NAME", "CONTENT_TYPE", "FILE_DATA", "CREATED_AT",
        ]
        placeholders = ", ".join(["?"] * (len(cols) - 1) + ["CURRENT_TIMESTAMP"])
        values = [getattr(paper, c) for c in PAPER_FIELDS] + [
            file_name or "",
            content_type or "",
            file_bytes if file_bytes else None,
        ]
        col_sql = ", ".join(f'"{c}"' for c in cols)
        with self._cursor() as cur:
            cur.execute(
                f'UPSERT "{_PAPERS}" ({col_sql}) VALUES ({placeholders}) WITH PRIMARY KEY',
                values,
            )
        self._invalidate(papers=True, domains=True)

    def remove_paper(self, paper_id: str) -> bool:
        with self._cursor() as cur:
            cur.execute(f'DELETE FROM "{_PAPERS}" WHERE "ID" = ?', [paper_id])
            removed = cur.rowcount > 0
        if removed:
            self._invalidate(papers=True, domains=True)
        return removed

    def paper_file(self, paper_id: str) -> StoredFile | None:
        with self._cursor() as cur:
            cur.execute(
                f'SELECT "FILE_DATA", "FILE_NAME", "CONTENT_TYPE" FROM "{_PAPERS}" WHERE "ID" = ?',
                [paper_id],
            )
            row = cur.fetchone()
        if row is None or row[0] is None:
            return None
        return StoredFile(
            data=_as_bytes(row[0]),
            content_type=row[2] or "application/pdf",
            file_name=row[1] or f"{paper_id}.pdf",
        )

    # -- deletions ---------------------------------------------------
    def deleted_ids(self) -> set[str]:
        if self._deleted_cache is not None:
            return self._deleted_cache
        with self._cursor() as cur:
            cur.execute(f'SELECT "ID" FROM "{_DELETED}"')
            self._deleted_cache = {r[0] for r in cur.fetchall()}
        return self._deleted_cache

    def add_deleted_id(self, paper_id: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                f'UPSERT "{_DELETED}" ("ID") VALUES (?) WITH PRIMARY KEY', [paper_id]
            )
        self._invalidate(deleted=True)

    # -- custom domains -------------------------------------------
    def custom_domains(self) -> list[str]:
        if self._domains_cache is not None:
            return self._domains_cache
        with self._cursor() as cur:
            cur.execute(f'SELECT "NAME" FROM "{_DOMAINS}" ORDER BY "NAME"')
            self._domains_cache = [r[0] for r in cur.fetchall()]
        return self._domains_cache

    def add_custom_domain(self, name: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                f'UPSERT "{_DOMAINS}" ("NAME") VALUES (?) WITH PRIMARY KEY', [name]
            )
        self._invalidate(domains=True)

    def remove_custom_domain(self, name: str) -> None:
        with self._cursor() as cur:
            cur.execute(f'DELETE FROM "{_DOMAINS}" WHERE LOWER("NAME") = LOWER(?)', [name])
        self._invalidate(domains=True)
