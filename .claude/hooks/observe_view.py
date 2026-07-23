#!/usr/bin/env python
"""Viewer for the agent-observability log written by observe.py.

Usage (from the project root):
    py .claude/hooks/observe_view.py             # pretty timeline of activity.log
    py .claude/hooks/observe_view.py --agents    # group tool calls by subagent
    py .claude/hooks/observe_view.py --tail 40   # last N lines of the timeline
    py .claude/hooks/observe_view.py --clear      # wipe the logs and start fresh
"""
import os
import sys
import json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OBS_DIR = os.path.join(os.path.dirname(HERE), "observe")  # .claude/observe
ACTIVITY = os.path.join(OBS_DIR, "activity.log")
EVENTS = os.path.join(OBS_DIR, "events.jsonl")


def show_timeline(tail=None):
    if not os.path.exists(ACTIVITY):
        print("No activity logged yet. Run a session with the hooks enabled first.")
        return
    with open(ACTIVITY, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if tail:
        lines = lines[-tail:]
    print("\n".join(lines))
    print(f"\n({len(lines)} lines shown from {ACTIVITY})")


def show_agents():
    """Group every logged event by which agent produced it."""
    if not os.path.exists(EVENTS):
        print("No events logged yet.")
        return
    by_agent = defaultdict(list)
    with open(EVENTS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            by_agent[rec.get("who", "main")].append(rec)

    for who, recs in by_agent.items():
        print(f"\n=== {who}  ({len(recs)} events) ===")
        for rec in recs:
            print(f"  [{rec.get('ts', '')}] {rec.get('summary', '')}")


def clear_logs():
    removed = []
    for path in (ACTIVITY, EVENTS):
        if os.path.exists(path):
            os.remove(path)
            removed.append(os.path.basename(path))
    print("Cleared: " + (", ".join(removed) if removed else "nothing to clear"))


def main():
    args = sys.argv[1:]
    if "--clear" in args:
        clear_logs()
    elif "--agents" in args:
        show_agents()
    elif "--tail" in args:
        i = args.index("--tail")
        n = int(args[i + 1]) if i + 1 < len(args) else 20
        show_timeline(tail=n)
    else:
        show_timeline()


if __name__ == "__main__":
    main()
