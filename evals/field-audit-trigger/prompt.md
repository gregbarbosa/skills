---
description: field-audit fires when the user asks to sweep and close dispatched agents.
tags: [trigger, field-audit]
runs: 3
plugins: ["../../skills/handoff", "../../skills/field-agent", "../../skills/field-handler", "../../skills/field-audit", "../../skills/herdr"]
max_turns: 4
allowed_tools: [Skill]
---

Sweep the field agents I dispatched earlier: read their results and close the panes that are finished.
