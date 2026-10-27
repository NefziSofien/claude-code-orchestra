---
name: verify-package
description: Run the right checks for a change in acme-backend, acme-web or acme-mobile - typecheck, lint, related tests - and report what passed and what was not run. Use before declaring work done, before a commit/push, and as the verifier step of /orchestrate.
---

<!-- EXAMPLE. Copy to <your-project>/.claude/skills/verify-package/SKILL.md and replace every command with the ones your packages really use. Test each command once before relying on it. -->

# Verify a package

Run inside the package directory, only for packages that changed. Fast checks first; stop and report on the first failure.

| Package | Fast (always) | Full (before push / when asked) |
|---|---|---|
| `acme-backend` | `npm run typecheck` · `npm run lint` · `npx jest --findRelatedTests --passWithNoTests <changed files>` | `npm run build` · `npm test` |
| `acme-web` | `npm run typecheck` · `npx eslint <changed files>` | `npm run lint` · `npm run build` |
| `acme-mobile` | `npm run typecheck` · `npx eslint <changed files>` · `npx jest --findRelatedTests --passWithNoTests <changed files>` | `npm test` |

Changed files: `git diff --name-only develop...HEAD` plus `git diff --name-only`. Never use `lint:fix` / `format` as a check: they rewrite files.

## Never run as a "check"

- End-to-end suites, unless the user's current message asks.
- Migrations, deploys, mobile store builds, anything pointed at staging or production.

## Report

```
PACKAGE: <name>  STATUS: pass | fail
RAN: <command → result>, one per line
FAILURES: <file:line - cause>, or -
NOT RUN: <check and why>, or -
```
