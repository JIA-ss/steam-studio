# Upstream provenance

- Repository: https://github.com/FronkonGames/Steam-Games-Scraper
- Revision: `cdbbddd9b01c7be2a9d80635c1b93b4936915252`
- Imported: 2026-09-28
- License: MIT; original copyright retained in `LICENSE.md` and source header.
- Original documentation: `README.upstream.md` (historical reference, not current instructions).

The first vendor commit contains the original Python collector/helpers, README, license and dependency files. Images, precomputed discarded IDs and Git metadata were intentionally omitted. The adapted collector retains the upstream store-text/metadata parser and public source approach. Original helpers and dependency files remain recoverable from that commit; they were removed from the current tree because their schema and dependencies no longer match the maintained entrypoint. Dependencies are locked at repository root.

## Local changes

- Explicit IDs without a key; catalog key read from environment, never stored in artifacts.
- Bounded iterative retries, explicit HTTP status handling, credential-safe errors, request spacing and timeout.
- Atomic files, per-record checkpointing, terminal manifests, explicit partial/stale/excluded states.
- Upcoming games retained, missing data kept distinct from zero, country/language forwarded correctly.
- Integer price units and currency retained instead of parsing localized formatted strings.
- Official Steam review summaries; SteamSpy tags/ownership optional and source-labelled.
- Raw envelopes retained for audit; no bundled historical blacklist, random traversal or automatic full-market run.

This is a vendored adaptation, not a Git submodule. Review upstream changes against the recorded revision, port relevant fixes and run offline + bounded live checks. Do not blindly replace the maintained file with upstream HEAD.
