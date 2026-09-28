# Interface acceptance — 2026-09-28

Scope: full authenticated AppID catalog + every bundled research source + resume and standalone-skill execution. **Not** full per-game collection and **not** a market research conclusion. No commercial API or model service was used for collector checks.

## Catalog

- `--catalog-only` completed locally using the configured environment key.
- 189,070 records; 189,070 unique IDs; monotonically sorted.
- Retrieval timestamp: `2026-09-28T15:17:34.776493+00:00`.
- Local catalog SHA-256: `bd847ad3907de9c2a72cc6ca2e3ccbcc86e26f59ea38d019af4beddb58f85def`.
- Raw catalog and credentials are not published. The list represents available Steam catalog IDs, not a guarantee of every historical/delisted game.

## Per-game coverage

11 distinct IDs were checked. Five catalog-spread cases were chosen deterministically at the first, quarter, midpoint, three-quarter and last positions; other cases exercised known free/paid games and negative paths. This selection validates behavior, not statistical representativeness.

| AppID | Case | Observed outcome |
|---|---|---|
| 413150 | Stardew Valley, paid | Store, official reviews and SteamSpy OK |
| 570 | Dota 2, free | All three sources OK |
| 10 | Counter-Strike, older release | All three sources OK |
| 1472600 | Catalog quartile | All three sources OK |
| 2661260 | Catalog midpoint, free | All three sources OK |
| 3892380 | Catalog three-quarter | Store/reviews OK; SteamSpy has no tag coverage |
| 5320830 | Latest catalog ID, upcoming | Store/reviews OK; SteamSpy no-name placeholder rejected as unavailable |
| 250820 | SteamVR | All three sources OK; Steam itself classifies this entry as a game |
| 440820 | Soundtrack/DLC | Explicitly excluded based on returned non-game type |
| 228980 | Store unavailable case | `success=false`; explicitly unavailable, not zero-valued data |
| 2147483647 | Invalid ID | `success=false`; explicitly unavailable |

Additional checks:

- AppID 413150 with `country=cn`, `language=schinese`: complete, price currency `CNY`.
- Isolated skill copy, outside the Git repository, executed with the documented `uv run --with requests` fallback: complete for 413150.
- A second run on that successful snapshot returned `skipped`, preserving its original fetch timestamp.
- All 19 regression tests pass after corrections, including new coverage-placeholder and unavailable-state cases.
- Skill frontmatter validation and whitespace checks pass.

## Fixes prompted by acceptance

SteamSpy may return an ownership range even when `name` is null. That placeholder is now retained only in raw evidence and is not promoted to an ownership estimate. Empty list tags are classified as missing coverage, not malformed transport. Steam store `success=false` is distinguished from network/schema errors. Source gaps keep the game/run partial; the tool does not claim complete data just because HTTP was 200.

The skill now distinguishes catalog/interface/full-detail scopes, documents multi-day full-detail cost and the current whole-JSON persistence limit, and supports Multica standalone imports without assuming a repository root.

## Limits

The earlier local proxy failure did not recur during this acceptance. Connectivity can still change. SteamSpy coverage gaps remain real and are not repaired by client code. Full-market detailed crawling, long-run storage scaling, review-text pagination and revenue estimation remain outside this acceptance. Do not claim all 189,070 games have populated details.
