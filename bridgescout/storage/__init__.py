"""Pluggable persistence for the admin paper library.

- On SAP BTP a HANA HDI container is bound (``VCAP_SERVICES.hana``): uploaded
  PDFs and their metadata, custom domains and seed-paper deletions live in HANA
  tables, so they survive Cloud Foundry restarts / restages.
- Locally (no binding) the same data is kept as JSON + PDF files under ``data/``.

Both back ends implement :class:`~bridgescout.storage.base.LibraryStore`.
"""

from __future__ import annotations

import json
import logging
import os

from bridgescout.config import DATA_DIR
from bridgescout.storage.base import PAPER_FIELDS, LibraryStore, StoredFile
from bridgescout.storage.filesystem import FilesystemLibraryStore

__all__ = ["LibraryStore", "StoredFile", "PAPER_FIELDS", "get_store", "reset_store"]

_log = logging.getLogger(__name__)
_store: LibraryStore | None = None


def _hana_credentials() -> dict | None:
    raw = os.getenv("VCAP_SERVICES")
    if not raw:
        return None
    try:
        services = json.loads(raw)
    except json.JSONDecodeError:
        return None
    for key in ("hana", "hana-cloud", "hanatrial", "managed-hana"):
        for binding in services.get(key, []):
            creds = binding.get("credentials") or {}
            if creds.get("host") and creds.get("schema") and creds.get("user"):
                return creds
    return None


def get_store() -> LibraryStore:
    """Return the process-wide library store, HANA-backed when a container is bound."""
    global _store
    if _store is not None:
        return _store

    creds = _hana_credentials()
    if creds is not None:
        try:
            from bridgescout.storage.hana import HanaLibraryStore

            _store = HanaLibraryStore(creds)
            _log.info("Library store: HANA HDI container (schema %s)", creds.get("schema"))
            return _store
        except Exception as exc:  # missing hdbcli, network, tables not deployed yet
            _log.warning("HANA store unavailable (%s); falling back to filesystem", exc)

    _store = FilesystemLibraryStore(DATA_DIR)
    _log.info("Library store: filesystem under %s", DATA_DIR)
    return _store


def reset_store() -> None:
    """Drop the cached store (tests)."""
    global _store
    _store = None
