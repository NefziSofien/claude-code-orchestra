# Optional: lock down the shell for background workers

Workers that run in the background can't answer permission prompts, so you will want to allow-list safe commands. Do that on top of a shell policy that refuses dangerous ones. This is the setup used with [lean-ctx](https://github.com/yvgude/lean-ctx); adapt it to your own tooling.

## 1. Route every command through one filtered tool

With lean-ctx, set the shell hook to deny native Bash so all commands go through `ctx_shell`, which enforces an allowlist:

```bash
lean-ctx config set shell_hook_mode deny
```

Then allow `ctx_shell` in `~/.claude/settings.json` and keep the raw shell tools on "ask":

```json
{
  "permissions": {
    "allow": ["mcp__lean-ctx__ctx_shell"],
    "ask": ["mcp__lean-ctx__shell", "mcp__lean-ctx__ctx_execute"]
  }
}
```

Result: allow-listed commands run without a prompt, everything else is refused.

## 2. Keep the allowlist tight

- Remove `sudo` from the allowlist (edit `shell_allowlist_extra` in `~/.config/lean-ctx/config.toml`).
- Add what your projects really need, one command at a time: `lean-ctx allow <cmd>`.
- A script called as `./gradlew` is matched by its name: allow `gradlew`, not only `./gradlew`.
- Inline interpreter code (`python3 -c`, `node -e`) is blocked; agents write a small script file instead.

## 3. Pre-allow read-only tools

Look at which read-only commands and MCP tools you use most, and add them to `permissions.allow` so workers never stall on them. Claude Code's `/fewer-permission-prompts` skill builds this list from your own transcripts.

Never allow-list anything that can run arbitrary code (`bash`, `python3`, `npx`, `npm run *`, `docker exec`), push, deploy or delete.
