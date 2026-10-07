---
description: No field skill fires for a small single-file task.
tags: [negative, field-agent, field-handler]
runs: 3
plugins: ["../../skills/handoff", "../../skills/field-agent", "../../skills/field-handler", "../../skills/field-audit", "../../skills/herdr"]
max_turns: 4
allowed_tools: [Skill]
---

In one function, the variable usr should be called user. What is the cleanest way to rename it safely?
