"""Dataset collection utilities.

Phase 1 built a single top-level domain, ``Disease`` (PubMed + arXiv). Phase 2
adds five method-rich domains (arXiv + OpenAlex) whose papers hold the kinds of
solutions BridgeScout should surface for disease research gaps.

Each domain becomes ``dataset/<Domain>/`` with real papers, open-access PDFs
where reachable, and a reproducible stratified 80/20 train/test split.

Entry points:
- :func:`bridgescout.datasets.builder.build_domain_dataset` (any registered domain)
- ``scripts/build_dataset.py --domain all``
- ``scripts/build_disease_dataset.py`` (Disease only, kept for compatibility)
"""

from bridgescout.datasets.builder import build_domain_dataset
from bridgescout.datasets.registry import DOMAINS, METHOD_DOMAINS, DomainSpec
from bridgescout.datasets.schema import DatasetRecord
from bridgescout.datasets.split import stratified_split

__all__ = [
    "DatasetRecord",
    "stratified_split",
    "build_domain_dataset",
    "DOMAINS",
    "METHOD_DOMAINS",
    "DomainSpec",
]
