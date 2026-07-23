#!/usr/bin/env python
"""Agent observability hook for Claude Code.

Reads a single hook-event JSON payload from stdin and appends:
  1. A full structured record to  .claude/observe/events.jsonl  (one JSON per line)
  2. A compact human-readable line to  .claude/observe/activity.log

Purpose: track which subagent is triggered, when, and what tools each one runs.

This is a pure logging hook. It must NEVER block tool execution:
it swallows all errors and always exits 0 with no stdout.
"""
import sys
import os
import json
from datetime import datetime


def tool_detail(tool, tool_input):
    """Return a short, human-readable hint of what a tool call is doing."""
    ti = tool_input or {}
    if tool == "Task":
        return ti.get("subagent_type", "?")
    if tool == "Bash":
        return (ti.get("command") or "").replace("\n", " ")[:100]
    if tool in ("Read", "Edit", "Write", "NotebookEdit"):
        return ti.get("file_path", "")
    if tool == "Grep":
        return "/" + (ti.get("pattern") or "") + "/"
    if tool == "Glob":
        return ti.get("pattern", "")
    if tool == "WebFetch":
        return ti.get("url", "")
    if tool == "Skill":
        return ti.get("skill", "")
    return ""


def build_summary(event, tool, tool_input, data):
    """Build a one-line human-readable summary for a hook event."""
    ti = tool_input or {}
    if event == "PreToolUse" and tool == "Task":
        agent = ti.get("subagent_type", "?")
        desc = (ti.get("description") or "").replace("\n", " ")
        return f"AGENT TRIGGERED  >>  [{agent}]  {desc}"
    if event == "PreToolUse":
        detail = tool_detail(tool, ti)
        return f"tool >  {tool}  {detail}".rstrip()
    if event == "PostToolUse":
        detail = tool_detail(tool, ti)
        return f"tool <  {tool}  {detail}  (ok)".rstrip()
    if event == "PostToolUseFailure":
        detail = tool_detail(tool, ti)
        resp = data.get("tool_response")
        if isinstance(resp, dict):
            err = str(resp.get("error") or resp.get("message") or resp)
        else:
            err = str(resp or data.get("error") or "")
        err = err.replace("\n", " ")[:80]
        return f"tool !  {tool}  {detail}  FAILED: {err}".rstrip()
    if event == "SubagentStop":
        return "SUBAGENT FINISHED  <<"
    if event == "SubagentStart":
        return f"SUBAGENT START  >>  [{data.get('agent_type', '?')}]"
    if event == "UserPromptSubmit":
        prompt = (data.get("prompt") or data.get("user_input") or "").replace("\n", " ")[:120]
        return f"USER PROMPT:  {prompt}"
    if event == "Stop":
        return "MAIN AGENT STOP"
    if event == "SessionStart":
        return f"===== SESSION START ({data.get('source', '')}) ====="
    if event == "SessionEnd":
        return f"===== SESSION END ({data.get('reason', '')}) ====="
    if event == "Notification":
        return f"NOTIFICATION:  {(data.get('message') or '')[:120]}"
    return event


def main():
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:
        pass

    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {"_parse_error": True, "_raw": raw[:2000]}

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    out_dir = os.path.join(project_dir, ".claude", "observe")

    try:
        os.makedirs(out_dir, exist_ok=True)

        event = data.get("hook_event_name", "Unknown")
        session = (data.get("session_id") or "")[:8]
        tool = data.get("tool_name", "")
        tool_input = data.get("tool_input", {}) or {}
        # agent_id / agent_type are present only when the hook fires INSIDE a
        # subagent, so they tell us which subagent ran this tool call.
        agent_id = data.get("agent_id") or ""
        agent_type = data.get("agent_type") or ""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        summary = build_summary(event, tool, tool_input, data)

        if agent_id:
            who = f"{agent_type or 'subagent'}#{agent_id[:6]}"
        else:
            who = "main"

        record = {
            "ts": ts,
            "event": event,
            "session": session,
            "who": who,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "tool": tool,
            "summary": summary,
            "payload": data,
        }
        with open(os.path.join(out_dir, "events.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        with open(os.path.join(out_dir, "activity.log"), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] ({session}) [{who:<16}] {summary}\n")
    except Exception:
        # Never let a logging failure interfere with the tool call.
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
