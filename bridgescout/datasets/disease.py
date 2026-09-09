"""The Phase-1 ``Disease`` domain: eight disease sub-areas, each queried against
both PubMed and arXiv so the corpus spans clinical and computational work on the
same conditions.

This module holds only the query config plus a thin wrapper; the actual
fetch -> dedupe -> PDFs -> 80/20 split lives in
:func:`bridgescout.datasets.builder.build_domain_dataset`.
"""

from __future__ import annotations

from pathlib import Path

from bridgescout.datasets.builder import _dedupe, build_domain_dataset
from bridgescout.datasets.pdfs import DEFAULT_MAX_PDF_BYTES

__all__ = ["DISEASE_AREAS", "DOMAIN", "build_disease_dataset", "_dedupe"]

DOMAIN = "Disease"

# Each area: a focused PubMed boolean (restricted to records that have an
# abstract) and a looser arXiv keyword query.
DISEASE_AREAS: dict[str, dict[str, str]] = {
    "Cardiovascular": {
        "pubmed": (
            '("cardiovascular diseases"[MeSH Terms] OR "myocardial infarction"[Title/Abstract] '
            'OR "heart failure"[Title/Abstract] OR "atrial fibrillation"[Title/Abstract]) '
            "AND hasabstract AND English[Language]"
        ),
        "arxiv": "cardiovascular disease OR ECG arrhythmia detection OR heart failure prediction",
    },
    "Oncology": {
        "pubmed": (
            '("neoplasms"[MeSH Terms] OR "tumor microenvironment"[Title/Abstract] '
            'OR "cancer immunotherapy"[Title/Abstract]) AND hasabstract AND English[Language]'
        ),
        "arxiv": "cancer detection deep learning OR tumor segmentation OR oncology histopathology",
    },
    "Neurological": {
        "pubmed": (
            '("nervous system diseases"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] '
            'OR "Parkinson disease"[Title/Abstract] OR "epilepsy"[Title/Abstract] '
            'OR "stroke"[Title/Abstract]) AND hasabstract AND English[Language]'
        ),
        "arxiv": "Alzheimer detection OR Parkinson gait OR epileptic seizure EEG OR stroke lesion",
    },
    "InfectiousDisease": {
        "pubmed": (
            '("communicable diseases"[MeSH Terms] OR "sepsis"[Title/Abstract] '
            'OR "tuberculosis"[Title/Abstract] OR "COVID-19"[Title/Abstract] '
            'OR "antimicrobial resistance"[Title/Abstract]) AND hasabstract AND English[Language]'
        ),
        "arxiv": "sepsis prediction OR tuberculosis chest x-ray OR COVID-19 diagnosis OR epidemic modeling",
    },
    "Respiratory": {
        "pubmed": (
            '("respiratory tract diseases"[MeSH Terms] OR "COPD"[Title/Abstract] '
            'OR "asthma"[Title/Abstract] OR "pneumonia"[Title/Abstract] '
            'OR "pulmonary fibrosis"[Title/Abstract]) AND hasabstract AND English[Language]'
        ),
        "arxiv": "COPD detection OR asthma monitoring OR pneumonia chest radiograph OR lung sound classification",
    },
    "MetabolicDiabetes": {
        "pubmed": (
            '("diabetes mellitus"[MeSH Terms] OR "metabolic syndrome"[Title/Abstract] '
            'OR "obesity"[Title/Abstract] OR "insulin resistance"[Title/Abstract]) '
            "AND hasabstract AND English[Language]"
        ),
        "arxiv": "diabetes prediction OR blood glucose forecasting OR diabetic retinopathy OR metabolic syndrome",
    },
    "Autoimmune": {
        "pubmed": (
            '("autoimmune diseases"[MeSH Terms] OR "rheumatoid arthritis"[Title/Abstract] '
            'OR "multiple sclerosis"[Title/Abstract] OR "systemic lupus erythematosus"[Title/Abstract] '
            'OR "inflammatory bowel disease"[Title/Abstract]) AND hasabstract AND English[Language]'
        ),
        "arxiv": "multiple sclerosis MRI OR rheumatoid arthritis OR lupus classification OR autoimmune biomarker",
    },
    "RenalKidney": {
        "pubmed": (
            '("kidney diseases"[MeSH Terms] OR "chronic kidney disease"[Title/Abstract] '
            'OR "acute kidney injury"[Title/Abstract] OR "dialysis"[Title/Abstract] '
            'OR "diabetic nephropathy"[Title/Abstract]) AND hasabstract AND English[Language]'
        ),
        "arxiv": "chronic kidney disease prediction OR acute kidney injury OR dialysis outcome OR renal segmentation",
    },
}


def build_disease_dataset(
    out_dir: Path,
    per_area: int = 50,
    pubmed_share: float = 0.5,
    test_ratio: float = 0.2,
    seed: int = 42,
    download_pdf: bool = True,
    areas: list[str] | None = None,
    api_key: str = "",
    arxiv_pause: float = 3.0,  # kept for CLI compatibility; builder paces arXiv itself
    max_pdf_bytes: int = DEFAULT_MAX_PDF_BYTES,
) -> dict:
    """Build ``dataset/Disease/`` from PubMed + arXiv (see module docstring)."""
    return build_domain_dataset(
        domain=DOMAIN,
        area_queries=DISEASE_AREAS,
        out_dir=out_dir,
        source_names=("pubmed", "arxiv"),
        per_area=per_area,
        source_shares={"pubmed": pubmed_share, "arxiv": 1.0 - pubmed_share},
        test_ratio=test_ratio,
        seed=seed,
        download_pdf=download_pdf,
        areas=areas,
        api_key=api_key,
        max_pdf_bytes=max_pdf_bytes,
    )
