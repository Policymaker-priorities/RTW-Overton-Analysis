import pandas as pd
import pytest

from overton import policy_cites
from overton.settings import Paths


def doc(i, cited, org="Government", dtype="Publication", title=None, country="USA",
        date="2021/05/01", source="src"):
    return {"Overton document ID": f"d{i}", "Document title": title or f"Doc {i}",
            "Document type": dtype, "Document series": None, "Cited DOIs": cited,
            "Publication date": date, "Overton source ID": source, "Source name": source,
            "Source organisation type": org, "Source country": country, "Overton URL": ""}


def test_doc_tier():
    tier = lambda *a: policy_cites.doc_tier(*a)[0]  # noqa: E731
    assert tier("Government", "Publication", "govuk", "The UK Government") == 1
    assert tier("Legislative Body", "Publication", "riksdag", "Sveriges Riksdag") == 1
    assert tier("Government", "Working paper", "ifausweden", "IFAU") == 1
    assert tier("Government", "Working paper", "ecb", "European Central Bank") == 2
    assert tier("Government", "Publication", "bankofireland", "Banc Ceannais na hÉireann") == 2
    assert tier("Government", "Publication", "euinvestbank", "European Investment Bank") == 1
    assert tier("IGO", "Working paper", "imf", "International Monetary Fund") == 3
    assert tier("Think Tank", "Publication", "brookings", "Brookings Institution") == 4
    assert tier("Think Tank", "Working paper", "nber", "NBER") is None
    assert tier("NGO", "Working paper", "x", "X") is None
    assert tier("Government", "Scholarly article", "govuk", "The UK Government") is None
    assert tier("Private Sector", "Publication", "x", "X") is None


def test_central_bank_names():
    cb = lambda name: policy_cites.is_central_bank("id", name, "Government")  # noqa: E731
    for name in ("Federal Reserve Bank of St Louis", "Bank of England", "Banco de España",
                 "Banca D'Italia", "Banque de France", "Deutsche Bundesbank", "Sveriges Riksbank",
                 "Österreichische Nationalbank", "Hong Kong Monetary Authority", "De Nederlandsche Bank"):
        assert cb(name), name
    for name in ("Government of Finland", "Bankruptcy Service", "Joint Research Centre"):
        assert not cb(name), name
    assert not policy_cites.is_central_bank("ecb", "European Central Bank", "IGO")


def test_region():
    assert [policy_cites.region(c) for c in ("USA", "IGO", "Germany", "EU", "Japan")] == \
        ["us", "international", "europe", "europe", "other"]


@pytest.fixture
def project(tmp_path):
    paths = Paths(tmp_path)
    paths.overton_queried.mkdir(parents=True)
    (paths.overton_queried / "batch.txt").write_text("10.1/a\nhttps://doi.org/10.1/B\n10.1/c\n",
                                                     encoding="utf-8")
    pd.DataFrame([
        doc(1, "10.1/a ; 10.9/other"),                                   # counts
        doc(2, "10.1/A", org="Think Tank", dtype="Working paper", source="nber"),  # excluded
        doc(3, "10.1/a", org="Think Tank", dtype="Publication", country="Germany"),
        doc(4, "10.1/a", title="Doc 1", date="2023/01/01"),             # duplicate of doc 1
        doc(5, "10.1/b", org="IGO", dtype="Working paper", country="IGO", date="2019/01/01"),
        doc(6, "10.1/zz"),                                               # cites nothing of ours
        doc(7, "10.1/b", title="성별 임금격차"),                         # Korean titles differ
        doc(8, "10.1/b", title="지역 경제"),
        doc(9, "10.1/a", dtype="Working paper", source="Federal Reserve Bank of Boston"),
    ]).to_csv(paths.overton_raw / "export.csv", index=False)
    return paths


def test_merge_counts(project):
    coded = pd.DataFrame({"doi": ["10.1/a", "10.1/b", "10.1/c", "10.1/d"],
                          "publication_year": [2018, 2016, 2020, 2020]})
    out, links, sources = policy_cites.merge(project, coded)
    out = out.set_index("doi")
    a, b, c, d = (out.loc[x] for x in ("10.1/a", "10.1/b", "10.1/c", "10.1/d"))
    # a: government doc 1 (tier 1), central-bank working paper doc 9 (tier 2), think-tank
    # report doc 3 (tier 4); the NBER working paper and duplicate doc 4 never count.
    assert [a[f"policy_cites_t{t}"] for t in (1, 2, 3, 4)] == [1, 2, 2, 3]
    assert a["policy_cites"] == 3 and a["policy_cited_t1"] == True        # noqa: E712
    assert a["policy_cites_government_legislature"] == 1 and a["policy_cites_central_bank"] == 1
    assert a["policy_cites_think_tank_ngo"] == 1 and a["policy_cites_igo"] == 0
    assert a["policy_cites_us"] == 2 and a["policy_cites_europe"] == 1
    assert a["policy_first_cite_year"] == 2021 and a["policy_years_to_first_cite"] == 3
    # b: two government docs (Korean titles kept apart) and an IGO working paper.
    assert [b[f"policy_cites_t{t}"] for t in (1, 2, 3, 4)] == [2, 2, 3, 3]
    assert b["policy_cites_international"] == 1
    assert c["policy_cites_t4"] == 0 and c["policy_cited_t1"] == False    # noqa: E712 - searched
    assert d["overton_queried"] == False and pd.isna(d["policy_cites_t1"])  # noqa: E712 - not searched
    assert "policy_cites_all" not in out.columns
    assert int(links["duplicate"].sum()) == 1
    nber = sources.set_index("source_id").loc["nber"]
    assert nber["excluded"] == 1 and nber["counted"] == 0
    assert project.papers_cited.exists() and project.overton_sources.exists()


def test_missing_inputs_are_errors(tmp_path):
    paths = Paths(tmp_path)
    with pytest.raises(FileNotFoundError):
        policy_cites.load_exports(paths)
    with pytest.raises(FileNotFoundError):
        policy_cites.queried_dois(paths)
