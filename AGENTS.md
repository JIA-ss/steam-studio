# Repository guidance

- Skill entrypoints live under `skills/<skill-name>/SKILL.md`; runnable tools belong inside the same skill's `tools/` directory.
- Keep this repository portable. Never commit personal absolute paths, secrets, collected datasets or private account data.
- Preserve upstream attribution and pinned revisions when adapting vendored code.
- Keep missing values, errors, estimates and observed zero distinct. Use explicit source timestamps and scoped validation claims.
- Run `uv run python -m unittest discover -s tests -v` for collector changes. Use bounded live checks only when needed; do not launch full-catalog scraping as a default test.
- Do not add model calls to deterministic collection or calculations. Optional semantic tooling must be documented and cannot be a hidden paid dependency.
