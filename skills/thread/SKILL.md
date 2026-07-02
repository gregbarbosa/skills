---
name: thread
description: Use ONLY when the user explicitly asks to launch or spawn a new agent thread in a herdr tab. Spawns a new agent in a fresh herdr tab — the harness (claude / glm / ds / opencode / pi, or whatever is in the harness registry) is chosen from the user's message and launched in that harness's native auto/yolo mode. Runs the user's request inside it and wires a fire-and-forget callback so the spawned agent pings the caller's pane when it finishes. Requires running inside herdr.
---

Before using this skill, check that `HERDR_ENV=1`. If it is not set to `1`, tell the user you are not running inside a herdr-managed pane and stop. Do not attempt the steps below from outside herdr.

When invoked, execute these steps immediately without asking for confirmation:

1. **Select the harness and prepare `<request>`.** Read the registry at `~/.claude/skills/thread/harnesses.json`. If it is missing or not valid JSON, fall back to this inline default and tell the user the config file was ignored:

   ```json
   { "default": "claude", "prompt_on_missing": true, "harnesses": [
     { "name": "claude",   "label": "Claude (Anthropic)", "command": "claude",   "auto_flag": "--permission-mode auto" },
     { "name": "glm",      "label": "GLM (Z.ai)",         "command": "glm",      "auto_flag": "--permission-mode auto" },
     { "name": "ds",       "label": "DeepSeek",           "command": "ds",       "auto_flag": "--permission-mode auto" },
     { "name": "opencode", "label": "OpenCode",           "command": "opencode", "auto_flag": "--auto" },
     { "name": "pi",       "label": "Pi",                 "command": "pi",       "auto_flag": "--approve" }
   ] }
   ```

   Detect the harness from the user's message and produce `<request>` (the message with the harness selection removed):
   - **Explicit form:** if the message starts with `--harness <name>` or `-h <name>`, select `<name>` and strip the flag + name from the message to form `<request>`. (Escape hatch for tasks that legitimately begin with a harness-named word.)
   - **Bare token:** otherwise, if the first whitespace-delimited token equals a registry `name`, select it and drop that token to form `<request>`.
   - **None:** otherwise leave the whole message as `<request>`. If `prompt_on_missing` is true, present a numbered menu of the harnesses (`1. <label>` … `N. <label>`; a blank reply picks `default`) and use the choice. If `prompt_on_missing` is false, silently use `default`.

   If the selected name is not in the registry, warn the user and fall back to the picker (or `default`).

   Worked examples (registry = the 5 above):
   | user's message | harness | `<request>` |
   |---|---|---|
   | `opencode refactor the auth module` | opencode | `refactor the auth module` |
   | `--harness glm fix the flaky test` | glm | `fix the flaky test` |
   | `-h pi summarize this thread` | pi | `summarize this thread` |
   | `ds the data layer needs indexing` | ds | `the data layer needs indexing` |
   | `refactor the auth module` | (none → picker; blank = claude) | `refactor the auth module` |
   | `claude review src/api` | claude | `review src/api` |

   Call the selected entry's `command` value `<command>` and its `auto_flag` value `<auto_flag>`.

2. Derive a short, descriptive tab label from `<request>` (max 30 chars, kebab-case or title case).
3. Capture YOUR OWN pane id so the spawned agent can call back. Get it LIVE from herdr — do NOT trust `$HERDR_PANE_ID`, which is set at shell startup and goes stale after a pane move (a stale id would send the finish-callback to a dead pane): `herdr pane current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])'`. Call this `<caller_pane>`. If it's empty (not running inside herdr — should not happen given the check above, but guard anyway), skip the callback wiring in step 9 and just note that to the user.
4. Find the current workspace ID from `herdr workspace list` (the focused one, or workspace 3 if there's a "Vox" workspace).
5. Create a new herdr tab with that label: `herdr tab create --workspace <N> --label "<label>"`
6. Parse the root pane ID from the JSON response (field: `result.root_pane.pane_id`). Call this `<pane_id>`. Also note the new pane's `cwd` from the response — if it differs from the directory the task concerns, pass ABSOLUTE paths in the request so the agent can find files regardless of its working directory.
7. Launch the harness in that pane with its native auto flag: `herdr pane run "<pane_id>" "<command> <auto_flag>"`.
8. Wait for the prompt: `herdr wait output "<pane_id>" --match "❯" --regex --timeout 60000`
9. Send `<request>` as the initial message, WITH a callback instruction appended so the agent pings the caller when done (omit the callback paragraph if `<caller_pane>` was empty in step 3):

   `herdr pane send-text "<pane_id>" "<request>\n\nWHEN YOU FINISH: notify the requesting agent by running these two commands so a message lands in their pane — herdr pane send-text \"<caller_pane>\" \"THREAD COMPLETE: <one-line summary of what you produced, incl. any file path>\"  then  herdr pane send-keys \"<caller_pane>\" Enter"`
10. Press Enter: `herdr pane send-keys "<pane_id>" Enter`
11. Report the tab label, pane ID, the caller pane the agent will call back to, and confirm the agent is running. Note that the callback is fire-and-forget (best-effort): if the spawned agent crashes before its final step the ping won't fire, so for critical work keep a fallback (ask, or check for the expected output file).

The user's request is the message they sent with this invocation, minus any harness-selection token consumed in step 1.
