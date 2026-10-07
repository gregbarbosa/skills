---
description: field-handler surfaces when work splits into independent strands, and offers before spawning.
tags: [trigger, field-handler]
runs: 3
plugins: ["../../skills/handoff", "../../skills/field-agent", "../../skills/field-handler", "../../skills/field-audit", "../../skills/herdr"]
max_turns: 4
allowed_tools: [Skill]
---

This afternoon I need three repos moved to the new auth token format: the API in ~/src/api, the web app in ~/src/web and the docs site in ~/src/docs. Each change is independent of the others. How should we tackle it?
