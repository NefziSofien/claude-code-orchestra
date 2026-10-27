# Token and model optimization

Coding agents spend most of their tokens re-reading context: the system prompt, tool lists, files, and command output, again on every request. An orchestrator multiplies that by the number of workers. This repo cuts the waste at six points. Measure first, then apply what your numbers point to.

## 1. Measure

```bash
python3 tools/usage-report.py            # last 30 days
python3 tools/usage-report.py --days 7
python3 tools/usage-report.py --json     # raw numbers
```

It reads your local Claude Code transcripts (nothing leaves your machine) and shows:

- tokens per model: input, cache write, cache read, output, and each model's share of output;
- cache read rate: the share of prompt tokens served from the prompt cache (cheaper and faster);
- subagent share: how much output comes from subagents rather than the main conversation;
- the projects, tools, MCP servers, skills and shell commands that cost the most;
- suggestions based on those numbers.

With lean-ctx installed, `lean-ctx gain` (and `gain --by-tool`, `gain --cost`) shows how much context it saved.

## 2. Route each job to the cheapest model that can do it

| Job | Agent | Model |
|---|---|---|
| Find code, map structure, list consumers of an API | `explorer` | Haiku |
| Run tests, build, lint, read the diff | `verifier` | Sonnet |
| Implement a unit that follows an existing pattern | `implementer` | same as the session |
| Architecture, API contracts, migrations, tricky logic | the main session, or `implementer` with `model: opus` | Opus |

The defaults live in each agent's front matter (`claude/agents/*.md`); the orchestrator overrides them per call only when a unit needs it. If the report shows one large model producing most of the output and no Haiku at all, searches are running on the expensive model.

## 3. Don't delegate what is cheaper to do inline

Every worker starts cold: it pays again for the system prompt, the tool list and whatever it has to re-read. So the orchestrator uses **0 workers** for anything under roughly 15 tool calls, **1 worker** for coupled work, and **at most 4** in parallel. More workers on a small task cost more and go worse.

## 4. Keep what crosses between agents small

- Briefs are a few lines: goal, files in scope, what "done" means, and at most 5 bullets of context. Never the whole conversation.
- Reports are 10 lines max, in a fixed format. The orchestrator keeps plans and reports, not file dumps.
- Progress lives in `.orchestra/state.md`, so after a context compaction the orchestrator re-reads one short file instead of re-deriving everything.

## 5. Compress reads and command output (lean-ctx)

See [`lean-ctx/README.md`](../lean-ctx/README.md). In short:

- reads go through `ctx_read`, which caches files and offers `map`, `signatures` and line-range modes, so the agent looks at the outline before reading 2,000 lines;
- searches go through `ctx_search` (compact results) instead of raw `grep`;
- shell output goes through `ctx_shell`, which compresses build and test logs;
- native `Grep` and `Glob` are denied so the cheap path is the only path.

## 6. Shrink what loads into every request

- **Plugins and MCP servers**: each one adds its tools and skill descriptions to every session and every worker, used or not. Check the "MCP servers" and "Skills" sections of the report and disable what you never use.
- **CLAUDE.md**: it is sent with every request. Keep it to rules that apply everywhere; move procedures into skills, which load only when needed (this repo's orchestration lives in a skill for that reason).
- **Prompt cache**: a high cache read rate means the stable part of the prompt is being reused. Editing CLAUDE.md or changing tools mid-session invalidates it, so batch those changes.

## 7. Avoid paid-for retries

A worker blocked on a permission prompt either stalls or burns tokens working around it. Pre-allow the read-only commands and tools you use most (Claude Code's `/fewer-permission-prompts` builds the list from your transcripts), and let the shell policy refuse the rest cleanly. The agents in this repo are told not to retry a refused command and to report what to allow instead.
