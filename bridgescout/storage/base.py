from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from bridgescout.ingestion.preprocessing import Paper

# The Paper fields persisted for an admin-uploaded library paper.
PAPER_FIELDS = (
    "id", "title", "domain", "abstract", "authors", "year",
    "limitations_text", "method_text", "source",
)


@dataclass
class StoredFile:
    data: bytes
    content_type: str
    file_name: str


def paper_record(paper: Paper) -> dict:
    return {k: getattr(paper, k) for k in PAPER_FIELDS}


def paper_from_record(record: dict) -> Paper:
    return Paper(**{k: record.get(k) for k in PAPER_FIELDS if record.get(k) is not None})


class LibraryStore(ABC):
    """Persistence for admin edits to the paper library: uploaded papers (metadata
    + PDF), custom domains, and deletions of bundled seed / corpus papers."""

    # -- uploaded papers -----------------------------------------------------
    @abstractmethod
    def uploaded_papers(self) -> list[Paper]: ...

    @abstractmethod
    def add_paper(
        self,
        paper: Paper,
        file_bytes: bytes | None,
        file_name: str | None,
        content_type: str | None,
    ) -> None: ...

    @abstractmethod
    def remove_paper(self, paper_id: str) -> bool:
        """Remove an uploaded paper (+ its file). Return True if one was removed."""

    @abstractmethod
    def paper_file(self, paper_id: str) -> StoredFile | None: ...

    # -- deletions of seed / corpus papers ---------------------------------
    @abstractmethod
    def deleted_ids(self) -> set[str]: ...

    @abstractmethod
    def add_deleted_id(self, paper_id: str) -> None: ...

    # -- custom (possibly empty) domains ---------------------------------
    @abstractmethod
    def custom_domains(self) -> list[str]: ...

    @abstractmethod
    def add_custom_domain(self, name: str) -> None: ...

    @abstractmethod
    def remove_custom_domain(self, name: str) -> None: ...
