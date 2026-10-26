"""Write the merged validation sample to an Excel workbook for review.

Inputs are the CSVs written by build_sample_data.py.
    python -I make_sample_xlsx.py <csv_dir> <dest.xlsx>
"""
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

src, dest = Path(sys.argv[1]), Path(sys.argv[2])
data = pd.read_csv(src / "sample_v02_cited.csv")
summary = pd.read_csv(src / "sample_cite_summary.csv")
links = pd.read_csv(src / "sample_links.csv")
sources = pd.read_csv(src / "sample_sources.csv")
authors = pd.read_csv(src / "sample_authors.csv")
changes = pd.read_csv(src / "sample_changes.csv")
compare = pd.read_csv(src / "sample_compare.csv")

TIERS = ["government & legislature", "central banks", "intergovernmental organisations",
         "think tanks & NGOs"]


def yes_no(v):
    if isinstance(v, bool) or str(v) in ("True", "False"):
        return "Yes" if str(v) == "True" else "No"
    return v


for c in data.columns:
    if data[c].dropna().astype(str).isin(["True", "False"]).all() and data[c].notna().any():
        data[c] = data[c].map(lambda v: yes_no(v) if pd.notna(v) else "")
for c in ("old", "new"):
    changes[c] = changes[c].map(yes_no)
changes["field"] = changes["field"].str.removeprefix("llm_").str.replace("cat_", "").str.replace("_", " ")

HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="1F4E78")
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")

wb = Workbook()
ws = wb.active
ws.title = "Read me"
intro = [
    ("Sources", "Each row combines three sources for one paper: OpenAlex (bibliographic data, authors "
     "and institutions, academic citations, topics), the LLM coding (codebook v0.2) and Overton "
     "(policy citations)."),
    ("What this is", "100 papers drawn at random from the Stage 1 dataset (16,147 research papers in 20 "
     "economics journals, 2016-2025), stratified by journal, all with abstracts. Each was coded by Claude "
     "(Opus 5.5) from its title, abstract and author affiliations alone, following codebook v0.2. "
     "Readability scores are computed directly from the abstract, not by the model."),
    ("Policy citations", "From Overton (export of 22 October 2026): the policy documents that cite each "
     "paper's DOI, counted at four levels of strictness (tiers T1 to T4) explained in the table below. "
     "All 100 DOIs were searched, so 0 means no citation was found."),
    ("Status", "Draft for review. The codebook will be refined after human coders code the same 100 "
     "papers and agreement is checked. The full dataset has not been coded yet."),
    ("Sheets", "'Merged sample': one row per paper: policy citations, then OpenAlex data, then the LLM "
     "coding. 'Authors': one row per author, with institution, country and coded discipline. "
     "'Citations by characteristic': share of papers cited, and mean citations, at each tier, by coded "
     "field (100 papers: descriptive only, no controls). 'Policy citations': every citing document, with "
     "the tier it counts at, or why it does not count. 'Citing sources': each citing organisation and "
     "its tier."),
    ("Codebook changes", "'Changes v0.1 to v0.2': answers that changed when the codebook was revised to "
     "define 'policy' narrowly (public bodies only) and to code unintended consequences only when the "
     "abstract presents an effect as a side effect. 'Field shares': how often each category was coded "
     "under each version."),
]
fields = [
    ("Policy citations T1-T4", "Number of citing policy documents at each tier (T4 is the broadest)."),
    ("Cited at T1-T4", "Yes when the paper has at least one citation at that tier."),
    ("From government & legislature / central banks / international organisations / think tanks & NGOs",
     "T4 citations split by the tier each document enters at; the four add up to T4."),
    ("T4 citations: US / Europe / international bodies / other", "T4 citations by where the citing "
     "organisation is."),
    ("First policy citation, Years to first", "Year of the earliest T4 citing document, and years after "
     "publication."),
    ("Academic citations (OpenAlex)", "Times cited by scholarly works, as of the OpenAlex harvest "
     "(12 October 2026)."),
    ("Field-weighted citation impact", "OpenAlex's citations relative to papers of the same field, year "
     "and type (1 = average)."),
    ("Authors / Institutions / Countries (n)", "Team size and spread, from OpenAlex's author affiliations."),
    ("OpenAlex topic, subfield, keywords", "OpenAlex's own classification (not the LLM's)."),
    ("In top-15 economics journals", "Stage 1 flag: journal is among the 15 core economics journals."),
    ("Item type", "research_article, review_article, or non_research (announcements, book reviews etc. "
     "that the Stage 1 filter missed)."),
    ("Topic", "Short plain-English label written by the model."),
    ("JEL codes (model)", "One to three JEL codes chosen by the model, most central first. OpenAlex has no "
     "JEL codes."),
    ("JEL codes (authors, if listed)", "Codes the authors printed in the abstract, in their (alphabetical) "
     "order; removed before coding and used to check the model's codes."),
    ("Research type", "theoretical / empirical / theory_and_empirical / econometric_methods / "
     "review_or_synthesis / other."),
    ("Empirical design", "experimental / quasi_experimental / structural / descriptive_or_correlational / "
     "forecasting_or_calibration / not_empirical."),
    ("Eight policy categories", "From the policymaker survey: proposes novel policy; causal effect of "
     "policy (on its intended outcomes); descriptive fact; unintended consequences; predicts effects with "
     "models; cost-benefit or welfare; identifies mechanisms; impacts on specific groups. Each is Yes/No "
     "independently, so a paper can be Yes on several or none."),
    ("Primary policy category", "The single category that best describes the paper, or none."),
    ("Policy studied", "none / existing_policy / proposed_or_hypothetical_policy / both."),
    ("Policy evaluation", "Computed: Yes when the paper is coded causal effect or unintended "
     "consequences AND uses an experimental, quasi-experimental or structural design."),
    ("Jargon, Sentence complexity", "Model ratings, 1 (plain, simple) to 5 (very technical, convoluted)."),
    ("Flesch reading ease, Flesch-Kincaid grade", "Standard readability formulas computed from the "
     "abstract. Lower reading ease / higher grade = harder to read."),
    ("Author disciplines", "Department of each author, in author order, coded from the affiliation text; "
     "'unknown' when the affiliation names no unit."),
    ("Multidisciplinary team", "Yes when authors come from two or more known disciplines; blank when no "
     "author's discipline could be determined."),
    ("Multidisciplinary beyond econ/business", "As above, but economics, finance and business count as "
     "one discipline."),
    ("Model notes", "The model's own note on anything uncertain."),
]
#: What each tier adds. Examples and counts are filled in from the data below.
TIER_ROWS = [
    ("T1", "Government and legislature",
     "Government departments, ministries and agencies (national, state and city), legislatures "
     "and their research services, the EU institutions. Central banks are NOT in T1."),
    ("T2", "T1 + central banks",
     "Adds central banks, including their research working papers. Overton files central banks as "
     "government; they are separated here because they are half of Overton's 'government' "
     "citations, mostly research working papers. Identified from the organisation's name."),
    ("T3", "T2 + international organisations",
     "Adds intergovernmental organisations, including their research working papers."),
    ("T4", "T3 + think tanks and NGOs",
     "Adds reports, briefs and other publications of think tanks and NGOs, but NOT their working "
     "papers. This is the broadest definition used."),
]
NEVER = ("Never counted", "",
         "Working papers from think tanks and NGOs. These include the academic working-paper series "
         "that Overton files as think tanks (NBER, IZA, ifo/CESifo, IFS). Also scholarly (journal) "
         "articles. A document listed more than once (re-issued, or co-published by two "
         "institutions) counts once.")
src_tier = sources.assign(t=sources["tier"])
r = 1
ws.cell(r, 1, "Overton analysis: merged sample dataset (OpenAlex + LLM coding + Overton policy "
        "citations)").font = Font(bold=True, size=14)
r += 2
for a, b in intro:
    ws.cell(r, 1, a).font = Font(bold=True)
    ws.cell(r, 1).alignment = TOP
    ws.cell(r, 2, b).alignment = WRAP
    r += 1

# -- citation tiers ----------------------------------------------------------
r += 1
ws.cell(r, 1, "POLICY CITATION TIERS").font = Font(bold=True, size=12)
ws.cell(r, 2, "Each tier includes everything in the tiers above it, so T1 is the strictest view "
        "of a policy citation and T4 the broadest. Every paper has a citation count and a "
        "'Cited at' Yes/No for each tier on the 'Merged sample' sheet.").alignment = WRAP
r += 1
heads = ["Tier", "What counts", "Example organisations (most documents counted at this tier, or "
         "most excluded, in the sample)",
         "Citations in sample", "Papers cited (of 100)"]
for c, h in enumerate(heads, start=1):
    cell = ws.cell(r, c, h)
    cell.font, cell.fill = HEAD, FILL
    cell.alignment = Alignment(wrap_text=True, vertical="center")
r += 1
for i, (tier, name, what) in enumerate(TIER_ROWS, start=1):
    top = src_tier[src_tier["t"] == i].sort_values("counted", ascending=False)["source_name"].head(4)
    ws.cell(r, 1, f"{tier}: {name}").font = Font(bold=True)
    ws.cell(r, 2, what)
    ws.cell(r, 3, "; ".join(top))
    count_col = next(c for c in data.columns if c.startswith(f"Policy citations {tier} ("))
    ws.cell(r, 4, int(data[count_col].sum()))
    ws.cell(r, 5, int((data[f"Cited at {tier}"] == "Yes").sum()))
    for c in range(1, 6):
        ws.cell(r, c).alignment = WRAP
    r += 1
ws.cell(r, 1, NEVER[0]).font = Font(bold=True)
ws.cell(r, 2, NEVER[2])
excl = src_tier.sort_values("excluded", ascending=False)["source_name"].head(4)
ws.cell(r, 3, "; ".join(excl))
for c in range(1, 6):
    ws.cell(r, c).alignment = WRAP
r += 2

# -- field definitions -------------------------------------------------------
for c, h in enumerate(("FIELD", "MEANING"), start=1):
    ws.cell(r, c, h).font, ws.cell(r, c).fill = HEAD, FILL
r += 1
for a, b in fields:
    ws.cell(r, 1, a).alignment = TOP
    ws.cell(r, 2, b).alignment = WRAP
    r += 1
for col, w in zip("ABCDE", (40, 110, 45, 12, 12)):
    ws.column_dimensions[col].width = w


def table(ws, df, widths, wrap_cols=(), freeze="A2"):
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append(["" if pd.isna(v) else v for v in row])
    for i, col in enumerate(df.columns, start=1):
        cell = ws.cell(1, i)
        cell.font, cell.fill = HEAD, FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = widths.get(col, 14)
        al = WRAP if col in wrap_cols else TOP
        for r in range(2, len(df) + 2):
            ws.cell(r, i).alignment = al
    ws.row_dimensions[1].height = 60
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions


ws = wb.create_sheet("Merged sample")
table(ws, data, {"Journal": 10, "Year": 7, "Title": 45, "DOI": 24, "Abstract": 80, "Topic": 30,
                 "Author disciplines": 30, "Model notes": 50, "OpenAlex ID": 32,
                 "JEL codes (model)": 16, "JEL codes (authors, if listed)": 18,
                 "Research type": 18, "Empirical design": 22, "Primary policy category": 24,
                 "Policy studied": 22, "Author names": 30, "Author institutions": 40, "Author countries": 14,
                 "Journal (full name)": 26, "OpenAlex topic": 30, "OpenAlex subfield": 22,
                 "OpenAlex keywords": 34, "Publication date": 12,
                 **{c: 12 for c in data.columns if c.startswith(("Policy citations T", "Cited at T", "From "))}},
      wrap_cols=("Title", "Abstract", "Topic", "Model notes", "Author disciplines", "Author names",
                 "Author institutions", "OpenAlex keywords"), freeze="D2")
for r in range(2, len(data) + 2):
    ws.row_dimensions[r].height = 150

ws = wb.create_sheet("Authors")
authors = authors.rename(columns={"title": "Paper", "author_order": "Author no.", "author_name": "Author",
                                  "author_position": "Position", "institutions": "Institution(s)",
                                  "countries": "Country", "institution_types": "Institution type",
                                  "discipline": "Discipline (coded)", "affiliation": "Affiliation as printed",
                                  "orcid": "ORCID", "openalex_id": "OpenAlex ID"})
authors = authors[["Paper", "Author no.", "Author", "Position", "Institution(s)", "Country",
                   "Institution type", "Discipline (coded)", "Affiliation as printed", "ORCID", "OpenAlex ID"]]
table(ws, authors, {"Paper": 45, "Author no.": 8, "Author": 24, "Position": 9, "Institution(s)": 38,
                    "Country": 9, "Institution type": 14, "Discipline (coded)": 24,
                    "Affiliation as printed": 60, "ORCID": 30, "OpenAlex ID": 32},
      wrap_cols=("Paper", "Institution(s)", "Affiliation as printed"), freeze="D2")

ws = wb.create_sheet("Citations by characteristic")
names = {"characteristic": "Characteristic", "value": "Value", "papers": "Papers"}
for t, label in enumerate(TIERS, start=1):
    names[f"share_cited_t{t}"] = f"Share cited, T{t}"
    names[f"mean_cites_t{t}"] = f"Mean citations, T{t}"
summary = summary.rename(columns=names)
table(ws, summary, {"Characteristic": 24, "Value": 30, "Papers": 9,
                    **{v: 11 for k, v in names.items() if "_t" in k}}, freeze="C2")
for i, col in enumerate(summary.columns, start=1):
    fmt = "0%" if col.startswith("Share") else "0.0" if col.startswith("Mean") else None
    if fmt:
        for r in range(2, len(summary) + 2):
            ws.cell(r, i).number_format = fmt
ws.cell(2, 1).font = Font(bold=True)

ws = wb.create_sheet("Policy citations")
links["Tier"] = links["tier_label"].where(~links["duplicate"], "")
links["Why not counted"] = links["rule"].where(~links["counts"], "")
links.loc[links["duplicate"], "Why not counted"] = "listed twice; counted once"
links = links.rename(columns={"title": "Cited paper", "doi": "Cited DOI", "document_title": "Citing document",
                              "document_type": "Document type", "document_series": "Series",
                              "citing_year": "Year", "source_name": "Citing organisation",
                              "source_type": "Organisation type (Overton)", "source_country": "Country",
                              "overton_url": "Overton link"})
links = links[["Cited paper", "Cited DOI", "Citing document", "Citing organisation",
               "Organisation type (Overton)", "Country", "Document type", "Series", "Year", "Tier",
               "Why not counted", "Overton link"]]
table(ws, links, {"Cited paper": 40, "Cited DOI": 24, "Citing document": 50, "Citing organisation": 32,
                  "Organisation type (Overton)": 15, "Country": 12, "Document type": 14, "Series": 20,
                  "Year": 7, "Tier": 30, "Why not counted": 30, "Overton link": 30}, freeze="C2")

ws = wb.create_sheet("Citing sources")
sources = sources.rename(columns={"source_id": "Overton source ID", "source_name": "Organisation",
                                  "source_type": "Organisation type (Overton)", "source_country": "Country",
                                  "tier_label": "Tier", "documents": "Citing documents",
                                  "counted": "Counted", "working_papers": "Working papers",
                                  "excluded": "Not counted"})
sources = sources[["Organisation", "Tier", "Organisation type (Overton)", "Country", "Citing documents",
                   "Counted", "Not counted", "Working papers", "Overton source ID"]]
sources = sources.sort_values(["Tier", "Citing documents"], ascending=[True, False])
table(ws, sources, {"Organisation": 50, "Tier": 32, "Organisation type (Overton)": 16, "Country": 14,
                    "Citing documents": 11, "Counted": 9, "Not counted": 9, "Working papers": 11,
                    "Overton source ID": 18}, freeze="B2")

ws = wb.create_sheet("Changes v0.1 to v0.2")
changes = changes.rename(columns={"openalex_id": "OpenAlex ID", "title": "Title", "field": "Field",
                                  "old": "v0.1", "new": "v0.2"})[["Title", "Field", "v0.1", "v0.2",
                                                                 "OpenAlex ID"]]
table(ws, changes, {"Title": 70, "Field": 30, "v0.1": 28, "v0.2": 28, "OpenAlex ID": 32},
      wrap_cols=("Title",), freeze="B2")

ws = wb.create_sheet("Field shares")
compare["field"] = compare["field"].str.replace("cat_", "").str.replace("_", " ")
compare = compare.rename(columns={"field": "Field", "n": "Papers", "agreement": "Same answer in both",
                                  "share_yes_old": "Share Yes, v0.1", "share_yes_new": "Share Yes, v0.2"})
table(ws, compare, {"Field": 32, "Papers": 9, "Same answer in both": 14, "Share Yes, v0.1": 14,
                    "Share Yes, v0.2": 14})
for col in ("C", "D", "E"):
    for r in range(2, len(compare) + 2):
        ws[f"{col}{r}"].number_format = "0%"

wb.save(dest)
print("wrote", dest)
