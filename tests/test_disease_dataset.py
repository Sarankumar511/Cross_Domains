from bridgescout.datasets.disease import DISEASE_AREAS, _dedupe
from bridgescout.datasets.schema import DatasetRecord
from bridgescout.datasets.sources import _parse_arxiv_xml, _parse_pubmed_xml
from bridgescout.datasets.split import stratified_split


def _record(idx: int, area: str) -> DatasetRecord:
    return DatasetRecord(
        id=f"pubmed-{idx}",
        source="pubmed",
        domain="Disease",
        sub_area=area,
        title=f"Paper {idx} on {area}",
        abstract=f"Abstract for paper {idx} about {area}.",
    )


def _corpus() -> list[DatasetRecord]:
    records = []
    n = 0
    for area, count in (("Cardiovascular", 50), ("Oncology", 50), ("RenalKidney", 3)):
        for _ in range(count):
            records.append(_record(n, area))
            n += 1
    return records


def test_post_init_fills_pipeline_text_fields():
    rec = DatasetRecord(
        id="x", source="arxiv", domain="Disease", sub_area="Oncology",
        title="t", abstract="the abstract body",
    )
    assert rec.limitations_text == "the abstract body"
    assert rec.method_text == "the abstract body"
    assert "arxiv_id" not in rec.to_dict() and "pmcid" not in rec.to_dict()
    assert set(rec.to_paper_dict()) == {
        "id", "title", "domain", "abstract", "authors", "year",
        "limitations_text", "method_text", "source",
    }


def test_split_ratio_is_roughly_80_20_overall():
    train, test = stratified_split(_corpus(), test_ratio=0.2, seed=42)
    total = len(train) + len(test)
    assert total == 103
    assert abs(len(test) / total - 0.2) < 0.03


def test_split_is_stratified_per_area():
    train, test = stratified_split(_corpus(), test_ratio=0.2, seed=42)
    train_areas = {r.sub_area for r in train}
    test_areas = {r.sub_area for r in test}
    assert train_areas == {"Cardiovascular", "Oncology", "RenalKidney"}
    assert test_areas == {"Cardiovascular", "Oncology", "RenalKidney"}
    # 50 -> 10 test, 3 -> 1 test (guaranteed >=1 when area has >=2)
    assert sum(1 for r in test if r.sub_area == "Cardiovascular") == 10
    assert sum(1 for r in test if r.sub_area == "RenalKidney") == 1


def test_split_has_no_leakage_and_covers_everything():
    corpus = _corpus()
    train, test = stratified_split(corpus, test_ratio=0.2, seed=7)
    train_ids = {r.id for r in train}
    test_ids = {r.id for r in test}
    assert train_ids.isdisjoint(test_ids)
    assert train_ids | test_ids == {r.id for r in corpus}
    assert all(r.split == "train" for r in train)
    assert all(r.split == "test" for r in test)


def test_split_is_deterministic_for_a_seed():
    a_train, a_test = stratified_split(_corpus(), seed=123)
    b_train, b_test = stratified_split(_corpus(), seed=123)
    assert [r.id for r in a_train] == [r.id for r in b_train]
    assert [r.id for r in a_test] == [r.id for r in b_test]


def test_dedupe_drops_repeat_ids_titles_and_dois():
    a = _record(1, "Oncology")
    b = _record(1, "Oncology")  # same id
    c = _record(2, "Oncology")
    c.title = a.title.upper()  # same title, different case
    d = _record(3, "Oncology")
    d.doi = "10.1/xyz"
    e = _record(4, "Oncology")
    e.doi = "10.1/XYZ"  # same doi
    kept = _dedupe([a, b, c, d, e])
    assert [r.id for r in kept] == ["pubmed-1", "pubmed-3"]


def test_area_config_is_well_formed():
    assert len(DISEASE_AREAS) == 8
    for area, queries in DISEASE_AREAS.items():
        assert area and area[0].isupper()
        assert queries["pubmed"].strip()
        assert queries["arxiv"].strip()
        assert "hasabstract" in queries["pubmed"]


def test_parse_pubmed_xml_extracts_core_fields():
    xml = """
    <PubmedArticleSet><PubmedArticle><MedlineCitation>
      <PMID>12345</PMID>
      <Article>
        <ArticleTitle>Deep learning for arrhythmia detection</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Noise is a problem.</AbstractText>
          <AbstractText Label="METHODS">We use a CNN.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>A</Initials></Author>
          <Author><LastName>Jones</LastName><Initials>B</Initials></Author>
        </AuthorList>
        <Journal><JournalIssue><PubDate><Year>2021</Year></PubDate></JournalIssue></Journal>
      </Article>
      <PubmedData><ArticleIdList>
        <ArticleId IdType="doi">10.1000/abc</ArticleId>
        <ArticleId IdType="pmc">PMC7777777</ArticleId>
      </ArticleIdList></PubmedData>
    </MedlineCitation></PubmedArticle></PubmedArticleSet>
    """
    rows = _parse_pubmed_xml(xml, "Cardiovascular")
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "pubmed-12345"
    assert row["sub_area"] == "Cardiovascular"
    assert "BACKGROUND: Noise is a problem." in row["abstract"]
    assert row["authors"] == "A Smith, B Jones"
    assert row["year"] == 2021
    assert row["doi"] == "10.1000/abc"
    assert row["pmcid"] == "PMC7777777"


def test_parse_arxiv_xml_extracts_core_fields():
    xml = """
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2401.01234v1</id>
        <title>Cross-domain signal denoising</title>
        <summary>We separate signal from noise.</summary>
        <published>2024-01-03T00:00:00Z</published>
        <author><name>Jane Doe</name></author>
      </entry>
    </feed>
    """
    rows = _parse_arxiv_xml(xml, "Neurological")
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "arxiv-2401.01234v1"
    assert row["arxiv_id"] == "2401.01234v1"
    assert row["abstract"] == "We separate signal from noise."
    assert row["year"] == 2024
    assert row["authors"] == "Jane Doe"
