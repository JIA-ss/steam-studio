# Validation record — 2026-09-28

Follow-up: [full catalog and expanded interface acceptance](interface-acceptance-20260928.md) succeeded locally after this initial smoke, with explicit upstream coverage gaps. It supersedes the earlier local connectivity limitation below; it does not establish full per-game coverage.

## Offline behavior

`uv run python -m unittest discover -s tests -v`

16 regression tests pass locally on Python 3.13 and in GitHub Actions on Python 3.10 and 3.13. [Offline CI run](https://github.com/JIA-ss/steam-studio/actions/runs/36439694139). Tests cover localized/missing prices, upcoming games, country/language forwarding, explicit zero reviews, failed enrichment, bounded 429/503 retries, Retry-After, credential-safe network errors, catalog pagination/cursor validation, atomic-save failure, resume, stale refresh, missing catalog key, non-game exclusion, inconsistent review totals and interrupted-run status.

The skill frontmatter/name validator also passes. These checks do not establish live availability or market completeness.

## Live checks

A local two-game run (AppIDs 413150 and 1145360, US/English) failed at the Steam storefront transport. The environment's configured proxy returned a failed CONNECT tunnel; direct curl also timed out during TLS connection. The collector reported errors, wrote a partial manifest and exited 2. No zero-valued substitute data was produced. Local raw data and network settings are not published.

The independent [manual live smoke run](https://github.com/JIA-ss/steam-studio/actions/runs/36439710805) **passed** on GitHub Actions at 2026-09-28 14:56 UTC, validating code revision `55c960834d731ec00d8cb90a10ce4e8e7a2cf92b`. Both AppIDs (413150 and 1145360) returned valid store metadata, USD integer prices, nonzero official review totals and nonempty SteamSpy tags. All three requested sources per app were `ok` and their raw files existed. This is six source payloads for two released paid games, not an all-market acceptance test.

SteamSpy was also independently reachable from the local environment (AppID 413150, HTTP 200, 20 tags). The local Steam storefront connection remains unresolved; use a functioning network/proxy, or the manual CI workflow for bounded verification. No global proxy configuration was changed.

The `Manual live smoke` workflow never runs automatically on push or pull request.

## Not yet validated

- Live authenticated full-catalog pagination (no Steam API key used).
- Full-market completion, long-running rate-limit behavior and data coverage.
- Live upcoming/unavailable app cases (covered by offline fixtures only).
- Sales/revenue model accuracy: no such model is shipped.
- Automated review-text pagination and market dashboards: not yet implemented.
