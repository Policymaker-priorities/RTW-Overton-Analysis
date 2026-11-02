# Instructions for AI agents

Read [HANDOVER.md](HANDOVER.md) first: it gives the current state and the ordered next steps. Then use [README.md](README.md) for commands and [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for columns.

## Rules

- **Tests:** run `python -m pytest` before and after changes. All tests are offline and should pass.
- **Citation tiers:** do not add academic working-paper series or an "everything" tier. See "Decisions already made" in the handover.
- **Codebook changes:** create a new codebook file and bump `LLM_CODEBOOK_VERSION` in `settings.py`, so earlier answers are not overwritten.
- **Wider harvests:** use `--root runs/<name>`. They must not touch `data/release/`.
- **Costs:** full coding runs and harvests use a paid plan or allowance. Confirm before starting one.
- **Commit:** everything that code cannot rebuild, such as `data/release/`, `data/raw/overton/` and `data/interim/llm/`. Never commit API keys.
- **Keep it current:** update HANDOVER.md when the state or next steps change.
