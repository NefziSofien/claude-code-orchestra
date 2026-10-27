# Contributing

Thanks for helping. Keep changes small and focused.

## Run the tests

Python 3, standard library only (no dependencies to install):

```bash
python3 -m unittest discover -s tests
```

CI also runs `shellcheck` on `*.sh` and PSScriptAnalyzer on `*.ps1`; run them locally if you touch those files. Validate a state file with `python3 tools/orchestra-validate.py .orchestra/state.md`.

## Conventions

- Python tools and hooks use the standard library only.
- Installers stay idempotent, back up existing files, and support `--dry-run` / `-DryRun`. Keep bash 3.2 (macOS) and Windows PowerShell 5.1 working.
- Worker reports keep the fixed format (STATUS, CHANGED, DECISIONS, OPEN, VERIFIED), 10 lines max.
- Match the surrounding style and comment density. Add or update a test when behavior changes.
- Do not use the Unicode em dash (U+2014) anywhere: use a comma, colon, period, hyphen or parentheses.
- No secrets, tokens, keys or personal paths in code, docs, fixtures or issues.
- No AI attribution in commits, PR descriptions or files.

## Pull request checklist

- [ ] Tests pass locally (`python3 -m unittest discover -s tests`)
- [ ] Added or updated tests for the change
- [ ] README or docs updated if behavior changed, and an entry added under Unreleased in CHANGELOG.md
- [ ] shellcheck / PSScriptAnalyzer clean if shell or PowerShell files changed
- [ ] No em dash, no secrets, no unrelated changes
