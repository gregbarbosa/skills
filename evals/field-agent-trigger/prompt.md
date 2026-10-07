---
description: field-agent fires when the user asks to hand one task to another agent.
tags: [trigger, field-agent]
runs: 3
plugins: ["../../skills/handoff", "../../skills/field-agent", "../../skills/field-handler", "../../skills/field-audit", "../../skills/herdr"]
max_turns: 4
allowed_tools: [Skill]
---

Spin up another agent in a new herdr tab to write unit tests for the parser while I keep working here.
