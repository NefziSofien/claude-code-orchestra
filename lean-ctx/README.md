# lean-ctx setup (optional, recommended)

[lean-ctx](https://github.com/yvgude/lean-ctx) is a local context layer for coding agents: it compresses file reads and shell output, caches files already read, and gives the agent cheaper ways to look at code (`map`, `signatures`, line ranges) before reading a whole file. With an orchestrator that runs several workers, every saved token is saved once per worker.

This folder adds two things on top of a plain lean-ctx install:

1. **A locked-down shell** so background workers can run safe commands without prompts and are refused everything else.
2. **Claude Code permissions** that match it: read tools and `ctx_shell` allowed, raw shell and script execution on "ask", native `Grep`/`Glob` denied so the agent uses the compressed tools.

lean-ctx is a separate project with its own license (see its repository). This repo only configures it.

## 1. Install lean-ctx

Linux and macOS (pick one):

```bash
curl -fsSL https://leanctx.com/install.sh | sh
brew tap yvgude/lean-ctx && brew install lean-ctx
npm install -g lean-ctx-bin
cargo install lean-ctx
```

Windows: lean-ctx recommends WSL, or building it with `cargo install lean-ctx`. See the lean-ctx README for the details.

## 2. Run the setup

```bash
./lean-ctx/setup.sh --dry-run
./lean-ctx/setup.sh            # add --privacy to turn telemetry off and limit file access to projects
```

```powershell
powershell -ExecutionPolicy Bypass -File .\lean-ctx\setup.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\lean-ctx\setup.ps1
```

What it does:

| Step | Command / file |
|---|---|
| Connect the agents | `lean-ctx wrap claude`, and `lean-ctx wrap cursor` if Cursor is installed |
| Route every shell command through the allowlist | `lean-ctx config set shell_hook_mode deny` |
| Privacy (with `--privacy`) | `lean-ctx telemetry off`, `lean-ctx config set path_jail_scope projects` |
| Claude Code permissions | merges [`claude-permissions.json`](claude-permissions.json) into `~/.claude/settings.json` (backup first, nothing removed except moving `shell`/`ctx_execute` from allow to ask) |
| Safety check | warns if `sudo` is in your lean-ctx allowlist |

Then restart Claude Code / Cursor and run `lean-ctx doctor`.

## 3. How the shell policy works

Each command passes three filters:

1. **Native Bash is denied.** With `shell_hook_mode = "deny"`, every command has to go through `ctx_shell`.
2. **Allowlist.** `ctx_shell` only runs commands on the allowlist; anything else is refused with a clear message. The agents in this repo are told not to retry or work around a refusal, and to tell you what to allow instead.
3. **No inline code.** `python3 -c` and `node -e` are blocked; agents write a small script file instead.

Keep the allowlist tight:

- Add what your projects need, one command at a time: `lean-ctx allow <cmd>`.
- A script called as `./gradlew` is matched by its name: allow `gradlew` (and `./gradlew` if you like).
- Remove `sudo` from `shell_allowlist_extra` in the lean-ctx config (`lean-ctx config path` shows where it is).
- Never allow-list in Claude Code anything that can run arbitrary code (`bash`, `python3`, `npx`, `npm run *`, `docker exec`), push, deploy or delete.

Tip: if a command you type yourself with `!` in Claude Code gets refused, run it from a normal terminal.

## 4. See what it saves

```bash
lean-ctx gain            # context saved so far
lean-ctx gain --by-tool  # per tool
lean-ctx gain --cost     # estimated cost per agent
lean-ctx doctor          # health check
```

For the model and token side (which model spends what, cache hit rate), run [`tools/usage-report.py`](../tools/usage-report.py). See [`docs/token-and-model-optimization.md`](../docs/token-and-model-optimization.md).

## Undo

```bash
lean-ctx unwrap claude
lean-ctx unwrap cursor
lean-ctx config set shell_hook_mode rewrite
```

Restore your previous `settings.json` from the `settings.json.bak-<timestamp>` the setup created.
