# Collector operations

Run from the repository root with Python 3.10+ and `uv sync --locked` (or install the single `requests` dependency). The tool is read-only against public Steam/SteamSpy endpoints. The only credential used is `STEAM_API_KEY` for catalog discovery; `.env.example` documents it but `.env` is not automatically loaded.

## Commands

```sh
# Small, keyless live sample. SteamSpy is opt-in; needed for tags.
uv run python skills/steam-research/tools/steam-games-scraper/SteamGamesScraper.py --appids 413150 1145360 --steamspy --data-dir data/smoke

# List all available game AppIDs. Set STEAM_API_KEY securely in your environment first.
uv run python skills/steam-research/tools/steam-games-scraper/SteamGamesScraper.py --catalog-only --data-dir data/catalog

# Resume bounded collection using the saved catalog; no key needed here.
uv run python skills/steam-research/tools/steam-games-scraper/SteamGamesScraper.py --catalog-file data/catalog/catalog.json --limit 100 --steamspy --data-dir data/research

# Explicitly process the whole saved catalog. Plan time and disk before invoking.
uv run python skills/steam-research/tools/steam-games-scraper/SteamGamesScraper.py --catalog-file data/catalog/catalog.json --all --steamspy --data-dir data/research
```

Use `--country cn --language schinese` for Chinese store metadata. Review summaries deliberately use **all languages and all purchase types**, independent of the store language. Prices retain the actual currency returned by Steam. Use separate data directories for different geographic snapshots or historical runs. One process per data directory; concurrent writers are not supported.

`--refresh` re-fetches existing successful records. Without it, complete records in the same country/language with requested sources present are reused and explicitly reported as skipped; partial/stale records retry. `--limit` selects the first N catalog IDs before resuming; it does not mean N new games. Increase the limit or use `--all` for wider coverage.

Minimum request interval: 1.5 seconds, including retries. Default 3 extra attempts (maximum 5), request timeout 20 seconds. HTTP 429 respects numeric Retry-After up to 60 seconds; larger/date-form waits stop the request rather than retry early. This does not guarantee an upstream quota; stop or slow down when rate-limited. Catalog paging and `appdetails` do not use SteamSpy's slower `request=all` route.

## Files and schema v1

- `catalog.json`: source URL, retrieval timestamp, AppID/name metadata; saved only after successful pagination. It contains no API key.
- `games.json`: object keyed by AppID. Includes upcoming games, free status, release text, country/language, store metadata, price integer units/currency, official review summary and optional SteamSpy tags/ownership estimate range.
- `raw/`: source JSON envelopes with timestamps and public request parameters. Latest raw fetches replace earlier ones in the same directory; use separate directories to preserve historical snapshots.
- `run.json`: selected and processed counts, per-ID status/source errors, timestamps and terminal status. Replaced each run; copy the directory to preserve a run history.

`status=ok` requires all requested sources to validate. `partial` retains useful fields when an enrichment fails. A failed refresh preserves the previous record as `stale`. Missing prices, unknown review totals and unavailable estimates stay `null`. `is_free` comes from Steam and is independent of missing price data. Non-game apps are explicitly `excluded`; unavailable games remain errors in the manifest and are not permanently blacklisted.

`price_final_minor` / `price_initial_minor` are Steam's raw integer price units; keep `currency` and `price_display` alongside them. Never parse a localized formatted price for calculations or compare different currencies without explicit conversion.

`review_summary` is from Steam's user-review endpoint, not editorial review text in store metadata. `steamspy.owners_estimate_range` remains a source-provided estimate string. SteamSpy-reported CCU is named `peak_ccu_yesterday_reported`; it is not a measured all-time peak. Missing SteamSpy playtime fields are not imported.

Exit codes: `0` selected records completed/reused/excluded; `2` partial/upstream/input/local-I/O failure; `130` interruption. Exit 0 never implies full-market coverage. Atomic JSON writes protect prior files. A hard kill can leave the last manifest `running`; inspect it and resume. Failed catalog retrieval leaves any earlier catalog file unchanged, so check freshness before reusing it.

## Connectivity

The HTTP client honors the proxy configuration discovered by Python requests. If a run reports `network_proxy_error`, check the configured proxy route; if it reports `network_tls_error`, check trust/certificate setup. Do not disable TLS verification to force a pass. A source failure must remain an error, not a zero record. The manual GitHub Actions smoke workflow is an independent network check, not a fix for local connectivity.

## Sources

- [App catalog](https://partner.steamgames.com/doc/webapi/IStoreService)
- [Official review query semantics](https://partner.steamgames.com/doc/store/getreviews)
- [SteamSpy API](https://steamspy.com/api.php)
- [SteamSpy limitations](https://steamspy.com/about)
- Store `appdetails` is a public storefront endpoint, not an equivalent stability guarantee to a documented Web API.
