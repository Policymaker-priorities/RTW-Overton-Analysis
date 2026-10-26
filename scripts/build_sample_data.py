"""Build the CSVs behind the sample workbook from the release files.

Run from the Overton-Analysis root with the project venv:
    .venv\\Scripts\\python <this> <out_dir>
Writes sample_v02_cited.csv, sample_cite_summary.csv, sample_links.csv,
sample_sources.csv, sample_authors.csv, sample_changes.csv, sample_compare.csv,
and data/release/sample_merged.csv.
"""
import sys

import pandas as pd

sys.path.insert(0, "src")
from overton import llm_assemble, llm_code, policy_cites  # noqa: E402
from overton.settings import Paths  # noqa: E402

out = sys.argv[1]
P = Paths()
OLD, NEW = "32461aa69458", llm_assemble.current_run_key(P)
TIER = policy_cites.TIERS

p = pd.read_csv(P.papers_cited, low_memory=False)
ids = set(pd.read_csv(P.validation_sample, dtype=str)["openalex_id"])
s = p[p["openalex_id"].isin(ids)].copy()
assert len(s) == 100 and s["overton_queried"].eq(True).all() and s["llm_coded_from"].eq("abstract").all()

# -- authors ------------------------------------------------------------------
a = pd.read_csv(P.authorships_stage1, low_memory=False)
a = a[a["openalex_id"].isin(ids)]


def join(v):
    return "; ".join(dict.fromkeys(x for x in v if isinstance(x, str) and x))


per_author = a.sort_values("author_order").groupby(["openalex_id", "author_order"]).agg(
    author_name=("author_name", "first"), author_position=("author_position", "first"),
    institutions=("institution_name", join), countries=("institution_country", join),
    institution_types=("institution_type", join), orcid=("orcid", "first")).reset_index()
team = per_author.groupby("openalex_id").agg(
    author_names=("author_name", join), author_institutions=("institutions", join),
    author_countries=("countries", join)).reset_index()
s = s.merge(team, on="openalex_id", how="left", validate="one_to_one")
disc = pd.read_csv(P.author_disciplines)
per_author = per_author.merge(disc[["openalex_id", "author_order", "discipline", "affiliation"]],
                              on=["openalex_id", "author_order"], how="left", validate="one_to_one")
per_author.merge(s[["openalex_id", "title"]], on="openalex_id").to_csv(f"{out}/sample_authors.csv", index=False)

# -- full merged CSV (analysis file) -------------------------------------------
drop = ["abstract", "raw_file", "harvest_date", "filter_version", "rules_fingerprint", "has_abstract",
        "abstract_word_count", "abstract_mentions_jel", "is_paratext", "is_retracted", "openalex_type",
        "language", "overton_queried"]
s.drop(columns=[c for c in drop if c in s.columns]).to_csv(P.release / "sample_merged.csv", index=False)

# -- main sheet ---------------------------------------------------------------
cats = llm_code.POLICY_CATEGORIES
cite_cols = {}
for t, label in TIER.items():
    scope = label if t == 1 else f"+ {label}"
    cite_cols[f"policy_cites_t{t}"] = f"Policy citations T{t} ({scope})"
for t in TIER:
    cite_cols[f"policy_cited_t{t}"] = f"Cited at T{t}"
cite_cols.update({
    "policy_cites_government_legislature": "From government & legislature",
    "policy_cites_central_bank": "From central banks",
    "policy_cites_igo": "From international organisations",
    "policy_cites_think_tank_ngo": "From think tanks & NGOs",
    "policy_cites_us": "T4 citations: US", "policy_cites_europe": "T4 citations: Europe",
    "policy_cites_international": "T4 citations: international bodies",
    "policy_cites_other_region": "T4 citations: other countries",
    "policy_cites_n_sources": "Distinct citing organisations (T4)",
    "policy_first_cite_year": "First policy citation (year, T4)",
    "policy_years_to_first_cite": "Years to first policy citation (T4)",
})
oa = {
    "cited_by_count": "Academic citations (OpenAlex)", "fwci": "Field-weighted citation impact",
    "referenced_works_count": "References", "n_authors": "Authors (n)",
    "n_institutions": "Institutions (n)", "n_countries": "Countries (n)",
    "author_names": "Author names", "author_institutions": "Author institutions",
    "author_countries": "Author countries", "source_display_name": "Journal (full name)",
    "publication_date": "Publication date", "volume": "Volume", "issue": "Issue",
    "page_count": "Pages", "primary_topic": "OpenAlex topic", "primary_subfield": "OpenAlex subfield",
    "keywords": "OpenAlex keywords", "is_oa": "Open access", "oa_status": "Open access status",
    "in_top15_economics_only": "In top-15 economics journals", "in_top15_all_fields": "In top-15 (all fields)",
}
coded = {
    "llm_item_type": "Item type", "llm_topic_label": "Topic",
    "llm_jel_codes": "JEL codes (model)", "jel_codes_author": "JEL codes (authors, if listed)",
    "llm_research_type": "Research type", "llm_empirical_design": "Empirical design",
    **{f"llm_cat_{c}": c.replace("_", " ").capitalize() for c in cats},
    "llm_primary_policy_category": "Primary policy category",
    "llm_policy_reference": "Policy studied", "llm_policy_evaluation": "Policy evaluation",
    "llm_jargon": "Jargon (1-5)", "llm_sentence_complexity": "Sentence complexity (1-5)",
    "abs_flesch_reading_ease": "Flesch reading ease", "abs_flesch_kincaid_grade": "Flesch-Kincaid grade",
    "author_disciplines": "Author disciplines", "multidisciplinary": "Multidisciplinary team",
    "multidisciplinary_beyond_econ_business": "Multidisciplinary beyond econ/business",
    "llm_notes": "Model notes",
}
front = {"journal_key": "Journal", "publication_year": "Year", "title": "Title", "doi": "DOI",
         "abstract_clean": "Abstract"}
cols = {**front, **cite_cols, **oa, **coded, "openalex_id": "OpenAlex ID"}
main = s.sort_values(["journal_key", "publication_year", "title"])[list(cols)].rename(columns=cols)
main.to_csv(f"{out}/sample_v02_cited.csv", index=False)

# -- citations by characteristic, one share-cited column per tier ---------------
q = s.copy()
for c in ("llm_policy_evaluation", "multidisciplinary"):
    q[c] = q[c].map({True: "Yes", False: "No"})
dims = [("llm_research_type", "Research type"), ("llm_empirical_design", "Empirical design"),
        ("llm_policy_evaluation", "Policy evaluation"),
        ("llm_primary_policy_category", "Primary policy category"),
        ("llm_policy_reference", "Policy studied"), ("multidisciplinary", "Multidisciplinary team"),
        ("llm_jel_primary_major", "JEL field (primary)"), ("publication_year", "Publication year"),
        ("journal_key", "Journal")]
parts = []
for col, label in dims:
    agg = {"papers": ("policy_cites_t4", "size")}
    for t in TIER:
        agg[f"share_cited_t{t}"] = (f"policy_cited_t{t}", "mean")
    for t in TIER:
        agg[f"mean_cites_t{t}"] = (f"policy_cites_t{t}", "mean")
    g = q.groupby(col).agg(**agg).reset_index().rename(columns={col: "value"})
    g.insert(0, "characteristic", label)
    parts.append(g.sort_values("papers", ascending=False))
allrow = {"characteristic": "All papers", "value": "", "papers": len(q),
          **{f"share_cited_t{t}": q[f"policy_cited_t{t}"].mean() for t in TIER},
          **{f"mean_cites_t{t}": q[f"policy_cites_t{t}"].mean() for t in TIER}}
pd.concat([pd.DataFrame([allrow])] + parts).to_csv(f"{out}/sample_cite_summary.csv", index=False)

# -- citing documents and sources -----------------------------------------------
links = pd.read_csv(P.citation_links)
links = links[links["doi"].isin(set(s["doi"]))].merge(s[["doi", "title"]], on="doi", how="left")
links["tier_label"] = links["tier"].map(lambda t: f"T{int(t)}: {TIER[int(t)]}" if pd.notna(t) else "")
links.to_csv(f"{out}/sample_links.csv", index=False)
src = pd.read_csv(P.overton_sources)
src["tier_label"] = src["tier"].map(lambda t: f"T{int(t)}: {TIER[int(t)]}" if pd.notna(t) else "not counted")
src.to_csv(f"{out}/sample_sources.csv", index=False)

# -- codebook comparison on the sample ------------------------------------------
summary, changed = llm_assemble.compare_runs(P, OLD, NEW)
changed[changed["openalex_id"].isin(ids)].to_csv(f"{out}/sample_changes.csv", index=False)
a_, b_ = (llm_assemble.assemble(P, k, write=False) for k in (OLD, NEW))
a_, b_ = (d[d["openalex_id"].isin(ids)].set_index("openalex_id") for d in (a_, b_))
rows = []
for f in llm_assemble.COMPARE_FIELDS:
    x, y = a_[f].map(llm_assemble._norm), b_[f].map(llm_assemble._norm)
    k = x.notna() & y.notna()
    r = {"field": f.removeprefix("llm_"), "n": int(k.sum()),
         "agreement": round(float((x[k] == y[k]).mean()), 3)}
    if set(x[k]) | set(y[k]) <= {"0", "1"}:
        r["share_yes_old"] = round(float((x[k] == "1").mean()), 3)
        r["share_yes_new"] = round(float((y[k] == "1").mean()), 3)
    rows.append(r)
pd.DataFrame(rows).to_csv(f"{out}/sample_compare.csv", index=False)
print("main", main.shape, "| links", len(links), "| sources", len(src))
