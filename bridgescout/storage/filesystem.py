from __future__ import annotations

import json
from pathlib import Path

from bridgescout.ingestion.preprocessing import Paper
from bridgescout.storage.base import (
    LibraryStore,
    StoredFile,
    paper_from_record,
    paper_record,
)


class FilesystemLibraryStore(LibraryStore):
    """JSON + PDF files under ``data/`` (local dev / no HANA binding)."""

    def __init__(self, data_dir: Path) -> None:
        self.upload_dir = data_dir / "uploads"
        self.uploads_json = self.upload_dir / "papers.json"
        self.deleted_json = data_dir / "deleted_papers.json"
        self.domains_json = data_dir / "domains.json"

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _read(path: Path) -> list:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    @staticmethod
    def _write(path: Path, data: list) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # -- uploaded papers -------------------------------------------------
    def uploaded_papers(self) -> list[Paper]:
        return [paper_from_record(r) for r in self._read(self.uploads_json)]

    def add_paper(self, paper, file_bytes, file_name, content_type) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        if file_bytes:
            (self.upload_dir / f"{paper.id}.pdf").write_bytes(file_bytes)
        records = [r for r in self._read(self.uploads_json) if r.get("id") != paper.id]
        records.append(
            {
                **paper_record(paper),
                "file_name": file_name or "",
                "content_type": content_type or "",
                "has_file": bool(file_bytes),
            }
        )
        self._write(self.uploads_json, records)

    def remove_paper(self, paper_id: str) -> bool:
        records = self._read(self.uploads_json)
        remaining = [r for r in records if r.get("id") != paper_id]
        if len(remaining) == len(records):
            return False
        self._write(self.uploads_json, remaining)
        pdf = self.upload_dir / f"{paper_id}.pdf"
        pdf.unlink(missing_ok=True)
        return True

    def paper_file(self, paper_id: str) -> StoredFile | None:
        record = next((r for r in self._read(self.uploads_json) if r.get("id") == paper_id), None)
        pdf = self.upload_dir / f"{paper_id}.pdf"
        if record is None or not pdf.exists():
            return None
        return StoredFile(
            data=pdf.read_bytes(),
            content_type=record.get("content_type") or "application/pdf",
            file_name=record.get("file_name") or f"{paper_id}.pdf",
        )

    # -- deletions -----------------------------------------------------
    def deleted_ids(self) -> set[str]:
        return {str(i) for i in self._read(self.deleted_json)}

    def add_deleted_id(self, paper_id: str) -> None:
        ids = self._read(self.deleted_json)
        if paper_id not in ids:
            ids.append(paper_id)
            self._write(self.deleted_json, ids)

    # -- custom domains ----------------------------------------------
    def custom_domains(self) -> list[str]:
        return [str(d).strip() for d in self._read(self.domains_json) if str(d).strip()]

    def add_custom_domain(self, name: str) -> None:
        names = self.custom_domains()
        if name.lower() not in {d.lower() for d in names}:
            self._write(self.domains_json, names + [name])

    def remove_custom_domain(self, name: str) -> None:
        self._write(
            self.domains_json,
            [d for d in self.custom_domains() if d.lower() != name.lower()],
        )
