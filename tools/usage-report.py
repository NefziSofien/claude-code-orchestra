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


USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


class Stats:
    """Everything aggregated from the transcripts."""

    def __init__(self):
        self.per_model = defaultdict(Counter)
        self.per_project = Counter()
        self.tools, self.mcp_servers, self.skills, self.agents, self.bash = (Counter() for _ in range(5))
        self.sidechain_out = 0
        self.seen_requests = set()
        self.sessions = set()


def find_transcripts(projects_dir):
    return glob.glob(os.path.join(projects_dir, "**", "*.jsonl"), recursive=True)


def filter_recent(files, days):
    """Return (files, since): transcripts modified within `days` days (0 = all)."""
    if not days:
        return files, None
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return [f for f in files if datetime.fromtimestamp(os.path.getmtime(f), timezone.utc) >= since], since


def read_records(path):
    """Yield the JSON objects of a transcript, skipping lines that are not valid JSON."""
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def is_before(record, since):
    if not since or not record.get("timestamp"):
        return False
    try:
        return datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")) < since
    except ValueError:
        return False


def count_tool_use(block, stats):
    name = block.get("name", "")
    inp = block.get("input") or {}
    stats.tools[name] += 1
    if name.startswith("mcp__"):
        stats.mcp_servers[name.split("__")[1]] += 1
    elif name == "Skill":
        stats.skills[inp.get("skill", "?")] += 1
    elif name in ("Agent", "Task"):
        stats.agents[f"{inp.get('subagent_type', 'general-purpose')} ({inp.get('model', 'default')})"] += 1
    elif name == "Bash":
        stats.bash.update(command_heads(inp.get("command", "")))


def count_usage(record, msg, project, stats):
    # One API response is split across several lines; count its usage once.
    key = record.get("requestId") or msg.get("id")
    usage = msg.get("usage")
    model = msg.get("model")
    if not usage or not model or model.startswith("<") or key in stats.seen_requests:
        return
    stats.seen_requests.add(key)
    u = stats.per_model[model]
    u["requests"] += 1
    for field in USAGE_FIELDS:
        u[field] += usage.get(field) or 0
    stats.per_project[project] += sum(usage.get(f) or 0 for f in USAGE_FIELDS)
    if record.get("isSidechain"):
        stats.sidechain_out += usage.get("output_tokens") or 0


def add_record(record, project, since, stats):
    if record.get("type") != "assistant" or is_before(record, since):
        return
    stats.sessions.add(record.get("sessionId"))
    msg = record.get("message") or {}
    for block in msg.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            count_tool_use(block, stats)
    count_usage(record, msg, project, stats)


def aggregate(files, projects_dir, since):
    stats = Stats()
    for path in files:
        project = project_name(os.path.relpath(path, projects_dir).split(os.sep)[0])
        for record in read_records(path):
            add_record(record, project, since, stats)
    return stats


def summarize(stats):
    """Derived numbers: (prompt tokens, cache read rate, total output tokens or 1)."""
    totals = Counter()
    for u in stats.per_model.values():
        totals.update(u)
    prompt = totals["input_tokens"] + totals["cache_creation_input_tokens"] + totals["cache_read_input_tokens"]
    cache_rate = totals["cache_read_input_tokens"] / prompt if prompt else 0
    return prompt, cache_rate, totals["output_tokens"] or 1


def render_json(stats, n_files, cache_rate, out_total):
    return json.dumps({
        "files": n_files, "sessions": len(stats.sessions), "models": stats.per_model, "projects": stats.per_project,
        "cache_read_rate": cache_rate, "subagent_output_share": stats.sidechain_out / out_total,
        "tools": stats.tools, "mcp_servers": stats.mcp_servers, "skills": stats.skills, "agents": stats.agents,
        "bash": stats.bash,
    }, indent=2, default=dict)


def render_top(title, counter, n=8):
    if not counter:
        return []
    return ["", title] + [f"  {count:>6}  {name}" for name, count in counter.most_common(n)]


def make_tips(stats, prompt, cache_rate, out_total):
    tips = []
    if stats.per_model:
        big = max(stats.per_model.items(), key=lambda kv: kv[1]["output_tokens"])
        cheap = [m for m in stats.per_model if "haiku" in m]
        if "opus" in big[0] and big[1]["output_tokens"] / out_total > 0.6 and not cheap:
            tips.append(f"{big[0]} produces {big[1]['output_tokens'] / out_total:.0%} of output and no Haiku is used: "
                        "send searches and file mapping to the `explorer` agent (Haiku).")
    if prompt and cache_rate < 0.5:
        tips.append("Under half of prompt tokens hit the cache: keep CLAUDE.md and the tool set stable during a session, "
                    "and avoid restarting long sessions.")
    if not stats.agents and len(stats.sessions) > 10:
        tips.append("No subagents used: big tasks run in one growing context. Try the `orchestrate` skill.")
    if stats.mcp_servers and "lean-ctx" not in stats.mcp_servers:
        tips.append("lean-ctx is not used: file reads and shell output go to the model uncompressed (see lean-ctx/README.md).")
    tips.append("Pre-allow the read-only commands and MCP tools you use most (Claude Code's /fewer-permission-prompts) "
                "so background workers never stall on a permission prompt.")
    tips.append("Disable plugins and MCP servers you never use: their tool lists load into every session and every worker.")
    return tips


def render_text(stats, days, n_files, prompt, cache_rate, out_total):
    period = f"last {days} days" if days else "all time"
    out = [f"Claude Code usage, {period}: {len(stats.sessions)} sessions, {n_files} transcript files\n",
           f"{'Model':<28}{'requests':>10}{'input':>10}{'cache write':>13}{'cache read':>12}{'output':>10}{'output %':>10}"]
    for model, u in sorted(stats.per_model.items(), key=lambda kv: -kv[1]["output_tokens"]):
        out.append(f"{model:<28}{u['requests']:>10}{fmt(u['input_tokens']):>10}{fmt(u['cache_creation_input_tokens']):>13}"
                   f"{fmt(u['cache_read_input_tokens']):>12}{fmt(u['output_tokens']):>10}{u['output_tokens'] / out_total:>10.0%}")
    out.append(f"\nCache read rate: {cache_rate:.0%} of prompt tokens came from the cache")
    out.append(f"Subagents: {stats.sidechain_out / out_total:.0%} of output tokens")
    out += ["", "Projects by tokens"]
    out += [f"  {fmt(count):>8}  {name}" for name, count in stats.per_project.most_common(8)]
    out += render_top("Tools", stats.tools)
    out += render_top("MCP servers", stats.mcp_servers)
    out += render_top("Skills", stats.skills)
    out += render_top("Subagents (type, model)", stats.agents)
    out += render_top("Shell commands", stats.bash)
    out += ["", "Suggestions"]
    out += [f"  - {t}" for t in make_tips(stats, prompt, cache_rate, out_total)]
    return "\n".join(out)


def main():
    args = parse_args()
    files = find_transcripts(args.projects_dir)
    if not files:
        print(f"No transcripts found in {args.projects_dir}", file=sys.stderr)
        return 1
    files, since = filter_recent(files, args.days)
    stats = aggregate(files, args.projects_dir, since)
    prompt, cache_rate, out_total = summarize(stats)
    if args.json:
        print(render_json(stats, len(files), cache_rate, out_total))
    else:
        print(render_text(stats, args.days, len(files), prompt, cache_rate, out_total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
