"""Stage 3: policy citations from Overton exports (no network).

Input: Overton's "policy documents" exports (one row per citing document, with
every DOI it cites in "Cited DOIs"), saved as CSV in data/raw/overton/, plus
a copy of each DOI list that was searched, in data/raw/overton/queried/, so a
paper that was searched and not cited gets 0 and one never searched stays blank.

Which citing documents count, as four nested tiers from strictest to broadest
(decided 2026-10-22 and 2026-10-26; each tier includes the ones before it):
1. government and legislative sources, central banks excepted;
2. + central banks (Overton files them as government);
3. + intergovernmental organisations (IMF, World Bank, OECD, BIS, ...);
4. + think tanks and NGOs, except their working papers.
Working papers of tiers 1-3 count; those of think tanks and NGOs never do, which
leaves out the academic series Overton files as think tanks (NBER, IZA
discussion papers, ifo/CESifo, IFS working papers) while keeping those
organisations' policy reports. Scholarly articles never count.

A citing document is counted once per paper even when Overton lists it more
than once (same title under one source, or one paper issued by two
institutions): documents are de-duplicated on normalised title.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .normalise import normalise_doi
from .settings import Paths

NON_PUBLIC_TYPES = frozenset({"Think Tank", "NGO"})
NEVER_TYPES = frozenset({"Scholarly article"})

TIERS = {
    1: "government & legislature",
    2: "central banks",
    3: "intergovernmental organisations",
    4: "think tanks & NGOs",
}

#: A government source is a central bank when its name matches; checked against
#: every government source in the sample export (Federal Reserve banks, "Bank of
#: England", "Banco de España", "Banc Ceannais na hÉireann", the Riksbank...).
_CENTRAL_BANK = re.compile(
    r"\bbank\b|\bbanco\b|\bbanca\b|\bbanque\b|bundesbank|riksbank|nationalbank|"
    r"federal reserve|monetary authority|ceannais|\bnederlandsche bank\b", re.IGNORECASE)
#: Government sources with a bank in the name that are not central banks.
NOT_CENTRAL_BANKS = frozenset({"euinvestbank"})  # European Investment Bank

#: Source countries counted as Europe (Overton uses "EU" for EU bodies).
EUROPE = frozenset({
    "EU", "UK", "Germany", "France", "Italy", "Spain", "Netherlands", "Belgium",
    "Luxembourg", "Ireland", "Sweden", "Finland", "Denmark", "Norway", "Iceland",
    "Switzerland", "Austria", "Portugal", "Greece", "Poland", "Czech Republic",
    "Slovakia", "Slovenia", "Hungary", "Estonia", "Latvia", "Lithuania", "Croatia",
    "Romania", "Bulgaria", "Malta", "Cyprus",
})

#: Runs of anything but letters and digits, in any script (Korean titles must not reduce to "").
_TITLE = re.compile(r"[\W_]+")


def region(country: str) -> str:
    if country == "USA":
        return "us"
    if country == "IGO":
        return "international"
    if country in EUROPE:
        return "europe"
    return "other"


def is_central_bank(source_id: str, source_name: str, org_type: str) -> bool:
    return (org_type == "Government" and source_id not in NOT_CENTRAL_BANKS
            and bool(_CENTRAL_BANK.search(str(source_name or ""))))


def doc_tier(org_type: str, doc_type: str, source_id: str = "",
             source_name: str = "") -> tuple[int | None, str]:
    """(tier 1-4 the citing document enters at, or None when it never counts; reason)."""
    if doc_type in NEVER_TYPES:
        return None, "scholarly article"
    if org_type == "Government" and is_central_bank(source_id, source_name, org_type):
        return 2, TIERS[2]
    if org_type in ("Government", "Legislative Body"):
        return 1, TIERS[1]
    if org_type == "IGO":
        return 3, TIERS[3]
    if org_type in NON_PUBLIC_TYPES:
        if doc_type == "Working paper":
            return None, "working paper from a think tank or NGO"
        return 4, TIERS[4]
    return None, f"organisation type {org_type!r} not covered"


def load_exports(paths: Paths) -> pd.DataFrame:
    files = sorted(paths.overton_raw.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"no Overton exports (*.csv) in {paths.overton_raw}")
    frames = [pd.read_csv(f, low_memory=False).assign(export_file=f.name) for f in files]
    d = pd.concat(frames, ignore_index=True)
    # The same document can appear in two exports (overlapping DOI batches).
    return d.drop_duplicates("Overton document ID").reset_index(drop=True)


def queried_dois(paths: Paths) -> set[str]:
    """DOIs actually searched in Overton: the lists saved in data/raw/overton/queried/."""
    files = sorted(paths.overton_queried.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"no searched-DOI lists (*.txt) in {paths.overton_queried}")
    out: set[str] = set()
    for f in files:
        out |= {normalise_doi(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}
    return out


def citation_links(docs: pd.DataFrame, dois: set[str]) -> pd.DataFrame:
    """One row per (paper DOI, citing document), with the inclusion rule applied."""
    rows = []
    for r in docs.to_dict("records"):
        cited = {normalise_doi(x) for x in str(r.get("Cited DOIs") or "").split(";") if x.strip()}
        tier, why = doc_tier(r["Source organisation type"], r["Document type"],
                             r["Overton source ID"], r["Source name"])
        year = str(r.get("Publication date") or "")[:4]
        for doi in sorted(cited & dois):
            rows.append({
                "doi": doi,
                "overton_document_id": r["Overton document ID"],
                "document_title": r["Document title"],
                "title_key": (_TITLE.sub(" ", str(r["Document title"] or "").casefold()).strip()
                              or r["Overton document ID"]),
                "document_type": r["Document type"],
                "document_series": r.get("Document series"),
                "citing_year": int(year) if year.isdigit() else None,
                "source_id": r["Overton source ID"],
                "source_name": r["Source name"],
                "source_type": r["Source organisation type"],
                "source_country": r["Source country"],
                "source_region": region(r["Source country"]),
                "tier": tier,
                "counts": tier is not None,
                "rule": why,
                "overton_url": r.get("Overton URL"),
            })
    links = pd.DataFrame(rows)
    # Count a document once per paper: later rows with the same paper and title are duplicates.
    links["duplicate"] = links.duplicated(["doi", "title_key"])
    return links


def paper_counts(links: pd.DataFrame, papers: pd.DataFrame, queried: set[str]) -> pd.DataFrame:
    """Per-paper citation measures. Papers whose DOI was not searched get blanks."""
    main = links[~links["duplicate"] & links["counts"]]
    pub = papers.set_index("doi")["publication_year"]
    rows = []
    for doi in papers["doi"].dropna():
        if doi not in queried:
            rows.append({"doi": doi, "overton_queried": False})
            continue
        m = main[main["doi"] == doi]
        years = m["citing_year"].dropna()
        first = int(years.min()) if len(years) else None
        row = {"doi": doi, "overton_queried": True}
        for t in TIERS:  # nested: tier t counts documents entering at tiers 1..t
            n = int((m["tier"] <= t).sum())
            row[f"policy_cites_t{t}"] = n
            row[f"policy_cited_t{t}"] = n > 0
        row.update({
            "policy_cites": len(m),
            "policy_cited_any": len(m) > 0,
            "policy_cites_government_legislature": int((m["tier"] == 1).sum()),
            "policy_cites_central_bank": int((m["tier"] == 2).sum()),
            "policy_cites_igo": int((m["tier"] == 3).sum()),
            "policy_cites_think_tank_ngo": int((m["tier"] == 4).sum()),
            "policy_cites_us": int((m["source_region"] == "us").sum()),
            "policy_cites_europe": int((m["source_region"] == "europe").sum()),
            "policy_cites_international": int((m["source_region"] == "international").sum()),
            "policy_cites_other_region": int((m["source_region"] == "other").sum()),
            "policy_cites_n_sources": int(m["source_id"].nunique()),
            "policy_first_cite_year": first,
            "policy_years_to_first_cite": (first - int(pub[doi]) if first is not None else None),
        })
        rows.append(row)
    return pd.DataFrame(rows)


def source_table(links: pd.DataFrame) -> pd.DataFrame:
    """One row per citing source: how many of its documents count and why, for review."""
    use = links[~links["duplicate"]]
    g = use.groupby(["source_id", "source_name", "source_type", "source_country"], dropna=False)
    out = g.agg(tier=("tier", "min"), documents=("counts", "size"), counted=("counts", "sum"),
                working_papers=("document_type", lambda s: int((s == "Working paper").sum())))
    out["excluded"] = out["documents"] - out["counted"]
    return out.reset_index().sort_values(["excluded", "documents"], ascending=False)


def merge(paths: Paths, coded: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(papers with citation columns, citation links, source table); writes all three."""
    docs = load_exports(paths)
    queried = queried_dois(paths)
    links = citation_links(docs, queried)
    counts = paper_counts(links, coded[["doi", "publication_year"]], queried)
    out = coded.merge(counts, on="doi", how="left", validate="many_to_one")
    sources = source_table(links)
    paths.release.mkdir(parents=True, exist_ok=True)
    out.to_csv(paths.papers_cited, index=False, encoding="utf-8")
    links.to_csv(paths.citation_links, index=False, encoding="utf-8")
    sources.to_csv(paths.overton_sources, index=False, encoding="utf-8")
    return out, links, sources
