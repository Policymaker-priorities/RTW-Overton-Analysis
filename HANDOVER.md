# Handover: Overton Analysis

*Written 2 November 2026 by Xavier Fletcher, at the end of their time on the project.*

**The question:** what types of economics research are more likely to be cited in policy documents? This is a predictive exercise, not a causal one. The end product is a set of graphs for the website, based on likelihood of citation.

**Companion project:** policymakers' statements, in [RTW-Speech-Scanner-V1](https://github.com/xav-fl/RTW-Speech-Scanner-V1).

## Where things stand

| Step | Status |
|---|---|
| 1. Collect papers from OpenAlex | **First cut done:** 20 journals, 2016–2025, 16,147 papers. **Full scope started:** 101 journals, 1986–2025 (102 config rows, because European Finance Review is the earlier name of Review of Finance and has its own OpenAlex record) |
| 2. Code paper characteristics with an LLM | **Pilot only:** 195 papers coded. Codebook v0.2 is still a draft, and the human check has not been done |
| 3. Add policy citations from Overton | **Pilot only:** 100 papers matched. The four citation tiers are built and working |
| 4. Clean and merge | **Pilot only:** a Stata cleaning script for the 100-paper sample is in `data/analysis/` |
| 5. Regressions and graphs | **Not started** |

## What to do next

1. **Finish the top-100 harvest.** The first attempt, on 2 November 2026, crashed on a dropped connection before saving any papers, so it needs starting again. The client does not retry that error, so consider adding a retry first. Running it costs only OpenAlex allowance. The commands are in the README under "Top-100 journals, 40 years". It stops when the daily allowance runs out (exit code 3), so run it again the next day and it resumes. Then run `normalise`, `filter` and `report` with the same `--root`, and check the filter still works on older papers.
2. **Get the codebook signed off.** Have people hand-code `data/review/llm_validation_sample.csv`, compare with `overton llm-agreement`, and refine. Do this before step 4, because a codebook change means re-coding.
3. **Decide what to do about missing abstracts** (see below).
4. **Code everything:** `overton llm-run --all`, then `llm-assemble`.
5. **Export citations for all papers from Overton.** The tiers need the per-citation export, which is limited to about 1,000 DOIs at a time. Ask Overton whether they can raise this limit, since they have indicated they may be flexible.
6. **Merge, extend the Stata cleaning beyond the pilot, and start the analysis.** The project leads planned to discuss the analysis at this point.

## Decisions already made

- **Citation tiers are nested:** T1 government and legislature, T2 adds central banks, T3 adds intergovernmental organisations, T4 adds think tanks and NGOs.
- **Academic working-paper series never count** (NBER, IZA, CESifo and so on). Overton files these as think tanks. A fifth "everything" tier was explicitly rejected.
- **Working papers from policy institutions do count** (tiers 1–3). They make up about a third of pilot citations, but only 6 of the 63 cited papers depend on them entirely.
- **Central banks get their own tier** because Overton files them as government, and they make up about half of "government" citations.

## Known problems

- **Abstract gap:** 28.1% of the 16,147 papers have no abstract, and 77% of those are in JAE, JFE, JoE and JME. Coding will therefore be thin for those journals, which biases comparisons. Filling them from Crossref or publishers may help, but this is untested.
- **Admin items:** 583 kept papers with no listed authors are flagged but still included. They need a decision.
- **Spot checks:** the samples in `data/review/` may never have had their human check.
- **Stale or stray files:** `reports/LLM_CODING_REPORT.md` describes the old v0.1 run. `data/release/~$overton_sample_merged_v0.2.xlsx` is an Excel lock file committed by accident. `papers_coded.csv` and `sample_merged.csv` are not in the README's data table.

## Access you will need

- **GitHub:** this repository is public under Xavier's personal account (`xav-fl`). Pushing needs collaborator access or a transfer.
- **Overton:** through Warwick's subscription, using the web interface.
- **OpenAlex:** your own API key in `OPENALEX_API_KEY`.
- **Claude:** a Claude Code sign-in (the default, which counts against plan limits) or `ANTHROPIC_API_KEY`. The README covers both.

## Where to find things

| What | Where |
|---|---|
| The data and how to run each stage | [README.md](README.md) |
| Every column in the main table | [DATA_DICTIONARY.md](DATA_DICTIONARY.md) |
| Rules the LLM codes by | [config/llm_codebook_v0.2.txt](config/llm_codebook_v0.2.txt) |
| Citation tier logic | [src/overton/policy_cites.py](src/overton/policy_cites.py) |
| Original Stage 1 specification | [OVERTON_STAGE1_BRIEF_v1.md](OVERTON_STAGE1_BRIEF_v1.md) |
