---
description: handoff fires when the user asks to prepare for a compaction.
tags: [trigger, handoff]
runs: 3
plugins: ["../../skills/handoff", "../../skills/field-agent", "../../skills/field-handler", "../../skills/field-audit", "../../skills/herdr"]
max_turns: 4
allowed_tools: [Skill]
---

My context is almost full and I'm mid-project. Prep a handoff so I can compact and pick up exactly where we left off.
