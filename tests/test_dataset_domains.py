import pytest

from bridgescout.datasets.builder import _source_quotas, build_domain_dataset
from bridgescout.datasets.registry import DOMAINS, METHOD_DOMAINS
from bridgescout.datasets.sources import _parse_openalex, _reconstruct_abstract


def test_registry_has_disease_plus_five_method_domains():
    assert set(DOMAINS) == {
        "Disease",
        "SignalProcessing",
        "EarthEnvironment",
        "Agriculture",
        "IndustrialReliability",
        "Finance",
    }
    assert set(METHOD_DOMAINS) == set(DOMAINS) - {"Disease"}


@pytest.mark.parametrize("name", sorted(DOMAINS))
def test_every_domain_spec_is_well_formed(name):
    spec = DOMAINS[name]
    assert spec.name == name
    assert len(spec.areas) >= 6
    assert spec.sources and all(s in {"pubmed", "arxiv", "openalex"} for s in spec.sources)
    for area, queries in spec.areas.items():
        assert area and area[0].isupper()
        for source in spec.sources:
            assert queries.get(source, "").strip(), f"{name}/{area} missing {source} query"


def test_method_domains_use_arxiv_plus_openalex():
    for name in METHOD_DOMAINS:
        assert DOMAINS[name].sources == ("arxiv", "openalex")


def test_sub_area_names_are_unique_and_filesystem_safe():
    for name, spec in DOMAINS.items():
        for area in spec.areas:
            assert area.isalnum(), f"{name}/{area} not filesystem-safe"


def test_source_quotas_split_evenly_and_absorb_rounding():
    assert _source_quotas(("arxiv", "openalex"), 50, None) == {"arxiv": 25, "openalex": 25}
    q = _source_quotas(("pubmed", "arxiv"), 50, {"pubmed": 0.5, "arxiv": 0.5})
    assert q == {"pubmed": 25, "arxiv": 25}
    # odd total: quotas still sum exactly to per_area, each close to the even share
    q = _source_quotas(("arxiv", "openalex"), 51, None)
    assert q["arxiv"] + q["openalex"] == 51
    assert all(abs(v - 25.5) <= 1 for v in q.values())


def test_build_domain_dataset_rejects_unknown_source(tmp_path):
    with pytest.raises(ValueError, match="Unknown source"):
        build_domain_dataset("X", {"A": {"bogus": "q"}}, tmp_path, source_names=("bogus",))


def test_reconstruct_abstract_orders_words_by_position():
    inv = {"Blind": [0], "source": [1], "separation": [2], "of": [3], "signals": [4]}
    assert _reconstruct_abstract(inv) == "Blind source separation of signals"
    assert _reconstruct_abstract(None) == ""
    assert _reconstruct_abstract({}) == ""


def test_parse_openalex_extracts_core_fields_and_pdf_hint():
    results = [
        {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1/abc",
            "title": "Deep denoising of seismic signals",
            "publication_year": 2022,
            "authorships": [
                {"author": {"display_name": "Jane Roe"}},
                {"author": {"display_name": "John Doe"}},
            ],
            "abstract_inverted_index": {"We": [0], "remove": [1], "noise.": [2]},
            "best_oa_location": {"pdf_url": "https://example.org/paper.pdf"},
        },
        {  # no abstract -> dropped
            "id": "https://openalex.org/W999",
            "title": "No abstract here",
            "abstract_inverted_index": None,
        },
    ]
    rows = _parse_openalex(results, "Seismology")
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "openalex-W123"
    assert row["source"] == "openalex"
    assert row["sub_area"] == "Seismology"
    assert row["abstract"] == "We remove noise."
    assert row["authors"] == "Jane Roe, John Doe"
    assert row["year"] == 2022
    assert row["doi"] == "10.1/abc"
    assert row["oa_pdf_url"] == "https://example.org/paper.pdf"
