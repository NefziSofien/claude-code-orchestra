#!/usr/bin/env python3
"""Token and model usage report for Claude Code, from your local session transcripts.

Reads ~/.claude/projects/**/*.jsonl (or $CLAUDE_CONFIG_DIR/projects), nothing is sent anywhere.
Shows tokens per model, cache hit rate, the projects and tools that cost the most, how much
work goes to subagents, and suggestions to spend fewer tokens.

Usage: python3 tools/usage-report.py [--days 30] [--projects-dir PATH] [--json]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--days", type=int, default=30, help="only sessions active in the last N days (default 30, 0 = all)")
    default_dir = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "projects")
    p.add_argument("--projects-dir", default=default_dir)
    p.add_argument("--json", action="store_true", help="print raw numbers as JSON")
    return p.parse_args()


def fmt(n):
    for unit in ("", "k", "M", "B"):
        if abs(n) < 1000:
            return f"{n:.0f}{unit}" if unit == "" else f"{n:.1f}{unit}"
        n /= 1000
    return f"{n:.1f}T"


SKIP_WORDS = {"cd", "for", "do", "done", "if", "then", "else", "fi", "while", "echo", "export", "set", "true", "{", "}", "(", ")"}


def command_heads(cmd):
    """Leading command of each segment of a shell line (split on && || ; | and newlines)."""
    heads = []
    lines = []
    for line in cmd.split("\n"):
        lines.append(line)
        if "<<" in line:  # the rest is a heredoc body, not commands
            break
    for segment in re.split(r"&&|\|\||;|\|", "\n".join(lines).replace("\n", ";")):
        words = segment.strip().split()
        while words and ("=" in words[0] or words[0] in ("sudo", "timeout", "env", "time", "nohup")):
            words = words[1:]
        if not words or words[0] in SKIP_WORDS or not re.match(r"^[\w./-]+$", words[0]):
            continue
        head = os.path.basename(words[0])
        if head in ("git", "gh", "npm", "pnpm", "yarn", "docker", "kubectl") and len(words) > 1 and not words[1].startswith("-"):
            head += " " + words[1]
        heads.append(head)
    return heads


def project_name(slug):
    """Turn '-home-alice-code-my-app' or 'C--Users-alice-code-my-app' into 'code-my-app'."""
    name = re.sub(r"^(-?home-[^-]+-|-?Users-[^-]+-|[A-Za-z]--Users-[^-]+-)", "", slug) or slug
    return name if len(name) <= 48 else name[:22] + "..." + name[-23:]


def main():
    args = parse_args()
    files = glob.glob(os.path.join(args.projects_dir, "**", "*.jsonl"), recursive=True)
    if not files:
        print(f"No transcripts found in {args.projects_dir}", file=sys.stderr)
        return 1
    since = None
    if args.days:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        files = [f for f in files if datetime.fromtimestamp(os.path.getmtime(f), timezone.utc) >= since]

    per_model = defaultdict(Counter)
    per_project = Counter()
    tools, mcp_servers, skills, agents, bash = Counter(), Counter(), Counter(), Counter(), Counter()
    sidechain_out = main_out = 0
    seen_requests = set()
    sessions = set()

    for path in files:
        project = project_name(os.path.relpath(path, args.projects_dir).split(os.sep)[0])
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("type") != "assistant":
                    continue
                if since and o.get("timestamp"):
                    try:
                        if datetime.fromisoformat(o["timestamp"].replace("Z", "+00:00")) < since:
                            continue
                    except ValueError:
                        pass
                sessions.add(o.get("sessionId"))
                msg = o.get("message") or {}
                for block in msg.get("content") or []:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = block.get("name", "")
                    inp = block.get("input") or {}
                    tools[name] += 1
                    if name.startswith("mcp__"):
                        mcp_servers[name.split("__")[1]] += 1
                    elif name == "Skill":
                        skills[inp.get("skill", "?")] += 1
                    elif name in ("Agent", "Task"):
                        agents[f"{inp.get('subagent_type', 'general-purpose')} ({inp.get('model', 'default')})"] += 1
                    elif name == "Bash":
                        bash.update(command_heads(inp.get("command", "")))
                # One API response is split across several lines; count its usage once.
                key = o.get("requestId") or msg.get("id")
                usage = msg.get("usage")
                model = msg.get("model")
                if not usage or not model or model.startswith("<") or key in seen_requests:
                    continue
                seen_requests.add(key)
                u = per_model[model]
                u["requests"] += 1
                for field in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"):
                    u[field] += usage.get(field) or 0
                total = sum(usage.get(f) or 0 for f in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
                per_project[project] += total
                if o.get("isSidechain"):
                    sidechain_out += usage.get("output_tokens") or 0
                else:
                    main_out += usage.get("output_tokens") or 0

    totals = Counter()
    for u in per_model.values():
        totals.update(u)
    prompt = totals["input_tokens"] + totals["cache_creation_input_tokens"] + totals["cache_read_input_tokens"]
    cache_rate = totals["cache_read_input_tokens"] / prompt if prompt else 0
    out_total = totals["output_tokens"] or 1

    if args.json:
        print(json.dumps({
            "files": len(files), "sessions": len(sessions), "models": per_model, "projects": per_project,
            "cache_read_rate": cache_rate, "subagent_output_share": sidechain_out / out_total,
            "tools": tools, "mcp_servers": mcp_servers, "skills": skills, "agents": agents, "bash": bash,
        }, indent=2, default=dict))
        return 0

    period = f"last {args.days} days" if args.days else "all time"
    print(f"Claude Code usage, {period}: {len(sessions)} sessions, {len(files)} transcript files\n")
    print(f"{'Model':<28}{'requests':>10}{'input':>10}{'cache write':>13}{'cache read':>12}{'output':>10}{'output %':>10}")
    for model, u in sorted(per_model.items(), key=lambda kv: -kv[1]["output_tokens"]):
        print(f"{model:<28}{u['requests']:>10}{fmt(u['input_tokens']):>10}{fmt(u['cache_creation_input_tokens']):>13}"
              f"{fmt(u['cache_read_input_tokens']):>12}{fmt(u['output_tokens']):>10}{u['output_tokens'] / out_total:>10.0%}")
    print(f"\nCache read rate: {cache_rate:.0%} of prompt tokens came from the cache")
    print(f"Subagents: {sidechain_out / out_total:.0%} of output tokens")

    def top(title, counter, n=8):
        if counter:
            print(f"\n{title}")
            for name, count in counter.most_common(n):
                print(f"  {count:>6}  {name}")

    print("\nProjects by tokens")
    for name, count in per_project.most_common(8):
        print(f"  {fmt(count):>8}  {name}")
    top("Tools", tools)
    top("MCP servers", mcp_servers)
    top("Skills", skills)
    top("Subagents (type, model)", agents)
    top("Shell commands", bash)

    tips = []
    if per_model:
        big = max(per_model.items(), key=lambda kv: kv[1]["output_tokens"])
        cheap = [m for m in per_model if "haiku" in m]
        if "opus" in big[0] and big[1]["output_tokens"] / out_total > 0.6 and not cheap:
            tips.append(f"{big[0]} produces {big[1]['output_tokens'] / out_total:.0%} of output and no Haiku is used: "
                        "send searches and file mapping to the `explorer` agent (Haiku).")
    if prompt and cache_rate < 0.5:
        tips.append("Under half of prompt tokens hit the cache: keep CLAUDE.md and the tool set stable during a session, "
                    "and avoid restarting long sessions.")
    if not agents and len(sessions) > 10:
        tips.append("No subagents used: big tasks run in one growing context. Try the `orchestrate` skill.")
    if mcp_servers and "lean-ctx" not in mcp_servers:
        tips.append("lean-ctx is not used: file reads and shell output go to the model uncompressed (see lean-ctx/README.md).")
    tips.append("Pre-allow the read-only commands and MCP tools you use most (Claude Code's /fewer-permission-prompts) "
                "so background workers never stall on a permission prompt.")
    tips.append("Disable plugins and MCP servers you never use: their tool lists load into every session and every worker.")
    print("\nSuggestions")
    for t in tips:
        print(f"  - {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
