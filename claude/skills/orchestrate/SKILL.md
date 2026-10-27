---
name: orchestrate
description: Orchestrate a large task across sub-sessions with compact context. Decomposes the task, decides how many workers to use (0, 1 or N independent units, max 4), routes each unit to a subagent or a separate session with the right model, keeps a compact state file that survives compaction, and verifies the merged result. Use when the user gives a big multi-part task, says "orchestrate", "dispatch", "split this up", "sub-sessions", or "/orchestrate".
argument-hint: <the big task>
---

# Orchestrate

You are the **orchestrator**. Your job is to plan, dispatch, track and verify, not to carry the detail of every unit in your own context. Keep your context small: briefs out, compact reports in.

## Resume (do this first)

At start, if `.orchestra/state.md` exists, read it before anything else. List the units whose status is not `done`, tell the user in one line, and continue from the first unfinished wave (the `Wave:` line) instead of re-decomposing. Re-plan only if the user's new request changes the task.

## 0. Load project rules first

Before decomposing, check the project's skills (`.claude/skills/`) for an `orchestrate-<project>` skill and any `verify-*` skill. If present, load them: their rules (unit boundaries, waves, brief contents, verification commands) override this skill. Name the relevant project skills in each worker's brief.

## 1. Decompose

Break the task into **units**. For each unit write one line:

```
U<n> | <goal, ≤12 words> | files/area: <paths or globs> | depends on: <U ids or -> | kind: read | write | design
```

Read just enough of the codebase to decompose correctly (structure + signatures, not full files). If you cannot tell which files a unit touches, use the `explorer` agent to find out before deciding.

## 2. Decide the number of workers

Apply in order, stop at the first that fits:

1. **0 workers (do it inline)**: the whole task fits in roughly 15 tool calls or fewer, or units are tiny. Delegation costs more than doing it. Say so in one line.
2. **1 worker**: the task is large but **coupled**: units depend on each other in a chain, share files, or must land in one change. One worker runs them in sequence (or do it inline if your context is still small).
3. **N workers**: N = number of units that are **truly independent**: no dependency on another unit's result, no shared files, no need to land in the same commit. **Cap N at 4**; group extra units into the 4 workers by area. Dependent units wait for a later wave.

Waves: units whose dependencies are done form the next wave. Re-apply the rule per wave.

**Before dispatching, show the user the plan in 6 lines or fewer** (units, waves, worker count, model per worker) and proceed unless the plan includes something irreversible (push, deploy, migration on a shared DB, deleting data). Then ask first.

**Cost guard:** before each wave, estimate rough token spend per worker (brief + files it reads + output; opus costs several times sonnet or haiku). If the wave looks large, ask the user first and state the estimate. Threshold used here: more than 3 workers on opus, or 4 workers on sonnet each reading many files, or any Agent Teams run. Below it, proceed.

## 3. Pick the vehicle for each worker

| Unit needs… | Use |
|---|---|
| A result you need back in this turn (research, audit, locate code, review) | **Subagent**: `Agent` tool, `subagent_type: explorer` / `verifier` |
| Code edits that are part of this same change | **Subagent**: `Agent`, `subagent_type: implementer`, `isolation: "worktree"` when 2 or more writers run at once |
| An independent deliverable of its own (own branch / PR, may outlive this turn, user may want to steer it) | **Separate session**: in the Claude desktop app use `start_session` (`context: "fresh"`, own worktree); in the CLI use `Agent` with `isolation: "worktree"` and `run_in_background: true` |
| Units that must coordinate with each other (share findings, challenge each other, cross-layer changes) and can own disjoint files | **Agent Teams** (experimental): teammates message each other and share a task list. Needs `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in env or settings.json `env`, interactive session only (not `-p`). Higher token cost, no `/resume` of in-process teammates, one team per session. Ask the user before enabling. Otherwise prefer subagents. |

Isolation: use Claude Code's native worktrees. `claude --worktree <name>` starts a session in its own worktree; inside a session use the `EnterWorktree` tool, or `isolation: "worktree"` on `Agent`. Prefer these over hand-made `git worktree` calls.

Never let two writers touch the same files. Read-only workers may share the checkout.

`isolation: "worktree"` only works when the working directory is a git repo. In a non-git workspace that holds several repos (for example one folder per package), isolate by scoping each writer to one repo folder; two writers in the same repo run in sequence, or each gets its own session started inside that repo.

## 4. Pick the model

- `haiku`: locating code, listing, grepping, summarizing files (the `explorer` agent default).
- `sonnet`: routine implementation, tests, checks (the `verifier` agent default).
- `opus` / inherit: architecture, tricky logic, cross-cutting refactors, anything design-heavy.

Pass `model` on the `Agent` call only to override the agent's default.

## 5. Write compact briefs

Each worker starts cold. Give it only what it needs: never the whole conversation, never "based on the findings above".

```
GOAL: <one sentence>
SCOPE: <files/dirs it may touch>; touch nothing else
CONTEXT: <5 bullets max: facts, decisions, conventions it needs>
DONE WHEN: <observable criteria: tests pass, endpoint returns X, file exists>
DO NOT: commit / push / switch branch (unless the unit is a separate session with its own branch)
SHELL: if a command is blocked by the shell policy, don't retry or reroute it; report what the user would need to allow under OPEN
REPORT: use the report format below, 10 lines max
```

If your setup routes shell commands through a specific tool (for example lean-ctx's `ctx_shell` with native Bash denied), say so in the SHELL line.

Report format every worker must return:

```
STATUS: done | partial | blocked
CHANGED: <files, one line>
DECISIONS: <non-obvious choices, 3 bullets max>
OPEN: <questions / risks, or ->
VERIFIED: <what was run and the result>
```

## 6. Track state in `.orchestra/state.md`

At the project root, create `.orchestra/state.md` and keep it current after every wave. It is the source of truth after a context compaction: if you lose track, re-read it first.

```markdown
# Task: <one line>
Updated: <ISO date-time>
Wave: <current wave number, e.g. 2/3>

## Units
| id | goal | worker | vehicle/model | status | branch/worktree |
|----|------|--------|---------------|--------|-----------------|

## Decisions
- ...

## Open questions
- ...

## Next
- ...
```

Keep it short: replace, don't append history. If the project is a git repo, add `.orchestra/` to `.git/info/exclude` (local, not committed) unless the user wants it tracked.

## 7. Integrate and verify

- Treat each report as a claim, not proof: check the diff or key files yourself (briefly).
- Worktree branches: **ask the user before merging** them here; never push them yourself. Name branches as `refs/heads/<name>`.
- Run the final check last (tests/build/lint over the whole result) via the `verifier` agent or inline. Say plainly what passed, what failed, and what could not be covered.
- On `partial`/`blocked`: fix inline if small, otherwise re-dispatch one targeted worker with a new brief that includes the blocker.

## Rules

- Small task: don't orchestrate; just do it and say so in one line.
- Never more than 4 parallel workers.
- Your context holds: the plan, the state file, the reports. Not file dumps.
- Follow the user's own git rules in every brief that involves git (commit message style, attribution, branch naming).
- Answer the user in the language they used.
