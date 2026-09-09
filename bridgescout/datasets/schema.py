from __future__ import annotations

from dataclasses import asdict, dataclass

# Fields that mirror bridgescout.ingestion.preprocessing.Paper so a collected
# record can be fed straight into the existing pipeline. The extra fields
# (sub_area, url, doi, pdf_*, split) are dataset-bookkeeping only.
PAPER_COMPATIBLE_FIELDS = (
    "id",
    "title",
    "domain",
    "abstract",
    "authors",
    "year",
    "limitations_text",
    "method_text",
    "source",
)


@dataclass
class DatasetRecord:
    id: str
    source: str  # "pubmed" | "arxiv"
    domain: str  # always "Disease" in this phase
    sub_area: str  # e.g. "Cardiovascular", "Oncology"
    title: str
    abstract: str
    authors: str = ""
    year: int | None = None
    url: str = ""
    doi: str = ""
    # arXiv gives only an abstract, and PubMed abstracts are not split into
    # "limitation" vs "method" sections, so both approximate to the abstract.
    limitations_text: str = ""
    method_text: str = ""
    pdf_path: str = ""  # POSIX path relative to the domain dir, "" if no PDF
    pdf_source: str = ""  # "arxiv" | "pmc-oa" | "oa-url" | ""
    split: str = ""  # "train" | "test", assigned by stratified_split
    # Resolver hints for the PDF downloader; stripped from the serialized record.
    arxiv_id: str = ""
    pmcid: str = ""
    oa_pdf_url: str = ""

    _HINT_FIELDS = ("arxiv_id", "pmcid", "oa_pdf_url")

    def __post_init__(self) -> None:
        if not self.limitations_text:
            self.limitations_text = self.abstract
        if not self.method_text:
            self.method_text = self.abstract

    def to_dict(self) -> dict:
        data = asdict(self)
        for hint in self._HINT_FIELDS:
            data.pop(hint, None)
        return data

    def to_paper_dict(self) -> dict:
        """Subset that matches the pipeline's Paper dataclass constructor."""
        return {k: getattr(self, k) for k in PAPER_COMPATIBLE_FIELDS}
