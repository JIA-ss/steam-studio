# Validation record — 2026-09-28

## Offline behavior

`uv run python -m unittest discover -s tests -v`

16 regression tests pass locally on Python 3.13. Tests cover localized/missing prices, upcoming games, country/language forwarding, explicit zero reviews, failed enrichment, bounded 429/503 retries, Retry-After, credential-safe network errors, catalog pagination/cursor validation, atomic-save failure, resume, stale refresh, missing catalog key, non-game exclusion, inconsistent review totals and interrupted-run status.

The skill frontmatter/name validator also passes. These checks do not establish live availability or market completeness.

## Live checks

A local two-game run (AppIDs 413150 and 1145360, US/English) failed at the Steam storefront transport. The environment's configured proxy returned a failed CONNECT tunnel; direct curl also timed out during TLS connection. The collector reported errors, wrote a partial manifest and exited 2. No zero-valued substitute data was produced. Local raw data and network settings are not published.

A separate manual GitHub Actions workflow (`Manual live smoke`) validates the same bounded, keyless sample from another network and checks returned IDs, prices/currency, positive review counts, tags and raw-source files. See repository Actions for current run results. It never runs automatically on push or pull request.

## Not yet validated

- Live authenticated full-catalog pagination (no Steam API key used).
- Full-market completion, long-running rate-limit behavior and data coverage.
- Live upcoming/unavailable app cases (covered by offline fixtures only).
- Sales/revenue model accuracy: no such model is shipped.
- Automated review-text pagination and market dashboards: not yet implemented.
