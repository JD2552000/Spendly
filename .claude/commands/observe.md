---
description: Show the subagent observability timeline from .claude/observe logs
argument-hint: "[--agents] [--tail N] [--clear]"
allowed-tools: Bash(py:*)
---

The output below is the current agent-observability log (written by the hooks in
`.claude/hooks/observe.py`). Present it to me clearly and, if useful, point out
which subagents ran and what tools each one used.

If the output is empty, tell me the hooks may not have fired yet — they only
activate on a fresh `claude` session after the hook-approval prompt is accepted.

!`py .claude/hooks/observe_view.py $ARGUMENTS`
