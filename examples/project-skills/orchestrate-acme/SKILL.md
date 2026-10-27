---
name: orchestrate-acme
description: Project-specific rules for /orchestrate in the acme workspace - how to split a large task across workers by package (backend, web, mobile), in which waves, with which brief. Use together with the global orchestrate skill whenever a big acme task is dispatched to subagents or sessions.
---

<!-- EXAMPLE. Copy to <your-project>/.claude/skills/orchestrate-<project>/SKILL.md, rename, and replace the package names, skills and commands with your own. -->

# Orchestrating acme work

Follow the global `orchestrate` skill; these rules override it for this workspace.

1. **Unit = one package.** Each `acme-*` folder is its own git repo, so units in different packages never share files. Split further inside a package only when the parts touch disjoint folders.
2. **No `isolation: "worktree"` at the workspace root**: it is not a git repo. Isolation comes from scoping each worker to one package folder. Two writers in the same package run in sequence, or each gets its own session started in that package.
3. **Waves for an API contract change:**
   - Wave 1: `acme-backend` (DTO, service, migration). The contract must be fixed before clients start.
   - Wave 2, in parallel: `acme-web` and `acme-mobile`, each briefed with the final request/response shape copied from the backend diff.
   Independent tasks with no shared contract can all run in wave 1.
4. **Every brief includes**: the package's own `CLAUDE.md` to read first; the relevant project skill (for example `new-endpoint`, `new-migration`, `web-feature`); the ticket id and the branch name pattern `<type>/<ticket>-<desc>` created from `develop`; "no commit, no push" unless the user said so.
5. **Models**: impact map / consumer search → `explorer`; backend contract and migrations → strongest model; client slices following an existing pattern → `implementer` default.
6. **Verification**: each worker ends with `verify-package` (fast checks) for its package; the final `verifier` runs the full column for every changed package. Never run e2e, migrations or deploys as part of orchestration.
7. **Production stays read-only**: no worker gets a brief that writes to production data, cloud projects or pipelines.
