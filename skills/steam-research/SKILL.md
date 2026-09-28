---
name: steam-research
description: Research Steam game markets and discover candidate game concepts from catalog, store, review and tag data. Use for open-ended topic selection, competitor screening and evidence-backed market comparisons, including when no genre is chosen. Does not publish games or edit Steamworks settings.
---

# Steam Research

Start with the user's decision, not a predetermined genre. When the user has no topic, build a market overview first, then narrow it using production constraints and player demand evidence. Do not require the user to supply candidate genres before research can begin.

## Tool entry

The maintained collector is [tools/steam-games-scraper/SteamGamesScraper.py](tools/steam-games-scraper/SteamGamesScraper.py), adapted from FronkonGames under MIT. Resolve the skill directory (including symlinks). If this is a repository checkout with `pyproject.toml` two levels above it, run the commands below from that repository root. A Multica-imported skill may be a standalone copy with no repository root: in that case run `uv run --with 'requests>=2.32.3,<3' python <absolute-skill-dir>/tools/steam-games-scraper/SteamGamesScraper.py ...` from the task workspace and use an absolute `--data-dir` there. Do not run `uv sync` in an unrelated directory or assume the repository layout exists. See [collector.md](references/collector.md) for setup, modes, schema and recovery, and [methodology.md](references/methodology.md) before interpreting market results.

Small public-data validation, without credentials:

```sh
uv sync --locked
uv run python skills/steam-research/tools/steam-games-scraper/SteamGamesScraper.py \
  --appids 413150 1145360 --steamspy --data-dir data/smoke
```

The catalog route requires `STEAM_API_KEY` in the environment. Explicit app IDs and an existing catalog file do not. Never read unrelated projects' secrets or publish keys, raw credentials or local datasets. No Steam login, paid service or model API is required by this collector.

## Workflow

1. Establish scope from existing context: market period, paid/free, released/upcoming, geography and known team/time/art constraints. Proceed with labelled assumptions where reasonable.
2. Distinguish full **catalog discovery**, full **interface acceptance**, and full **per-game collection**. Catalog discovery returns IDs, not game details. Interface acceptance needs cases across source/region/release/type states and expected failures; it is not a market-wide sample. Full per-game collection can take days and needs explicit scope, time/disk planning and resumable state. Check collection health on a small sample; inspect `run.json` and source status, not only exit code. Then collect the authorized scope. Default is 20 games; `--all` explicitly removes the limit. A low-AppID sample is a connectivity check, not representative market research.
3. Audit coverage and missingness. Keep unavailable games, missing tags and source failures visible in denominators. Use `--refresh` when current data is required; resume otherwise reuses recorded snapshots.
4. Analyze across tag combinations, release cohorts and price ranges. Report group size, review-count distributions and threshold shares, not just top sellers. Keep free, upcoming, DLC and paid full games distinct. Use the same release-age windows where dates and evidence support them.
5. Shortlist directions with inspectable game examples and evidence. Read original player reviews for finalists; the bundled collector currently gets review summaries, not paginated review text. Use the official review API separately with documented filters, pagination and bounded scope when that text is needed.
6. Deliver candidate directions, production implications, supporting AppIDs/URLs, snapshot dates, coverage gaps and next validation experiments. Do not infer team size, profit or development cost solely from store metadata.

Program code owns collection, filtering, calculations, state and verification. Use the primary model for open-ended interpretation. If a semantic classifier is useful for a large candidate set, explain its inputs and criterion first; preserve per-record sources and unresolved cases. Jev is optional and must not become an implicit dependency of this public skill.

## Evidence boundaries

- Missing is `null`, not zero; failure is not evidence of no demand. Distinguish source `unavailable` (coverage/region gap) from `error` (transport/schema failure). A partial run may be correct handling of expected missingness, but must not be reported as fully populated.
- SteamSpy owners are estimates of ownership, not units sold. Do not multiply owners by current list price and label it revenue.
- Tags overlap; groups are not mutually exclusive. Steam genres/categories are not interchangeable with user tags.
- Current online players are not daily active users or retention. Historical trends require dated snapshots; review timestamps alone do not reconstruct exact historical totals.
- An `ok` source response proves collection, not estimator accuracy. The full store is not necessarily a complete historical universe of delisted products.
