---
name: thread
description: Use ONLY when the user explicitly asks to launch or spawn a new agent thread in a herdr tab. Spawns a new Claude Code (or a user-specified binary) in a fresh herdr tab, runs the user's request inside it, and wires a fire-and-forget callback so the spawned agent pings the caller's pane when it finishes. Requires running inside herdr.
---

Before using this skill, check that `HERDR_ENV=1`. If it is not set to `1`, tell the user you are not running inside a herdr-managed pane and stop. Do not attempt the steps below from outside herdr.

When invoked, execute these steps immediately without asking for confirmation:

1. Derive a short, descriptive tab label from the user's request (max 30 chars, kebab-case or title case).
2. Capture YOUR OWN pane id so the spawned agent can call back: `echo "$HERDR_PANE_ID"` (e.g. `w653…:p9`). Call this `<caller_pane>`. If it's empty (not running inside herdr — should not happen given the check above, but guard anyway), skip the callback wiring in step 8 and just note that to the user.
3. Find the current workspace ID from `herdr workspace list` (the focused one, or workspace 3 if there's a "Vox" workspace).
4. Create a new herdr tab with that label: `herdr tab create --workspace <N> --label "<label>"`
5. Parse the root pane ID from the JSON response (field: `result.root_pane.pane_id`). Call this `<pane_id>`. Also note the new pane's `cwd` from the response — if it differs from the directory the task concerns, pass ABSOLUTE paths in the request so the agent can find files regardless of its working directory.
6. Launch Claude Code in that pane with auto-mode: `herdr pane run "<pane_id>" "claude --permission-mode auto"`. (If the user asked for a specific binary — e.g. `ds` — use that instead of `claude`.)
7. Wait for the prompt: `herdr wait output "<pane_id>" --match "❯" --regex --timeout 60000`
8. Send the full user request as the initial message, WITH a callback instruction appended so the agent pings the caller when done (omit the callback paragraph if `<caller_pane>` was empty in step 2):

   `herdr pane send-text "<pane_id>" "<the user's request>\n\nWHEN YOU FINISH: notify the requesting agent by running these two commands so a message lands in their pane — herdr pane send-text \"<caller_pane>\" \"THREAD COMPLETE: <one-line summary of what you produced, incl. any file path>\"  then  herdr pane send-keys \"<caller_pane>\" Enter"`
9. Press Enter: `herdr pane send-keys "<pane_id>" Enter`
10. Report the tab label, pane ID, the caller pane the agent will call back to, and confirm the agent is running. Note that the callback is fire-and-forget (best-effort): if the spawned agent crashes before its final step the ping won't fire, so for critical work keep a fallback (ask, or check for the expected output file).

The user's request is the message they sent with this invocation.
