---
name: thread
description: Use ONLY when the user explicitly asks to launch or spawn a new agent thread in a herdr tab. Spawns a new agent in a fresh herdr tab — the harness (claude / glm / ds / opencode / pi, or whatever is in the harness registry) is chosen from the user's message and launched in that harness's native auto/yolo mode. Runs the user's request inside it and wires a fire-and-forget callback so the spawned agent pings the caller's pane when it finishes. Requires running inside herdr.
---

Before using this skill, check that `HERDR_ENV=1`. If it is not set to `1`, tell the user you are not running inside a herdr-managed pane and stop. Do not attempt the steps below from outside herdr.

When invoked, execute these steps immediately without asking for confirmation:

1. **Select the harness and prepare `<request>`.** Read the registry at `harnesses.json` in **this skill's own directory** — the `Base directory for this skill:` path shown at the top of this skill (so it resolves for both global `~/.claude/skills/thread/` and project-level `.claude/skills/thread/` installs). If that file is missing or not valid JSON, fall back to this inline default and tell the user the config file was ignored:

   ```json
   { "default": "claude", "prompt_on_missing": true, "harnesses": [
     { "name": "claude",   "label": "Claude (Anthropic)", "command": "claude",   "auto_flag": "--permission-mode auto" },
     { "name": "glm",      "label": "GLM (Z.ai)",         "command": "glm",      "auto_flag": "--permission-mode auto" },
     { "name": "ds",       "label": "DeepSeek",           "command": "ds",       "auto_flag": "--permission-mode auto" },
     { "name": "opencode", "label": "OpenCode",           "command": "opencode", "auto_flag": "--auto" },
     { "name": "pi",       "label": "Pi",                 "command": "pi",       "auto_flag": "--approve" }
   ] }
   ```

   Flag semantics differ per harness (verified 2026-07-02): `--permission-mode auto` (claude-family) and `opencode --auto` auto-approve tool permissions; pi has no permission prompts at all — its `--approve` instead skips the project-local-files trust prompt at startup, which would otherwise block readiness.

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
8. **Wait for readiness via agent-status, not prompt glyphs.** Harness TUIs differ (claude/glm/ds show `❯`; pi shows a status line; opencode shows an "Ask anything…" box), but herdr's agent detection normalizes them: a pane goes `unknown → idle` once any recognized harness TUI is ready. Run:

   `herdr wait agent-status "<pane_id>" --status idle --timeout 60000`

   If that times out, fall back before giving up: read the pane (`herdr pane read "<pane_id>"`). If the output shows a shell error (`command not found`, crash/stack trace), report the launch failure to the user and stop. If it shows a TUI that simply wasn't status-detected, wait ~5s more and proceed to step 9 anyway — send-text is harmless to a ready TUI.

   Do NOT use agent-status to detect *completion* later: terminal statuses vary by harness (pi ends `done`, opencode has been observed stuck at `working` after finishing). Completion is signaled only by the callback in step 9.
9. Send `<request>` as the initial message, WITH a callback instruction appended so the agent pings the caller when done (omit the callback clause if `<caller_pane>` was empty in step 3). **Keep the whole payload on ONE line — do NOT insert `\n`/`\n\n` as a separator.** Under bracketed paste, embedded newlines do not submit (only the Enter in step 10 does), and they slow paste ingest, widening the step-10 race that leaves the prompt stuck unsent in the input box. Use a ` || ` sentinel instead of a blank line, and single-quote the callback so nothing needs escaping inside the double-quoted payload:

   `herdr pane send-text "<pane_id>" "<request>  ||  WHEN YOU FINISH: notify the requesting agent so a message lands in their pane — run  herdr pane send-text '<caller_pane>' 'THREAD COMPLETE: <one-line summary incl. any file path>'  then  herdr pane send-keys '<caller_pane>' Enter"`

10. **Submit with verification, not a blind Enter.** The paste ingests asynchronously; an Enter fired immediately as a *separate* request can land before the TUI commits the text and be dropped — the intermittent "text sits in the input box, never sent" bug. Poll, don't fixed-sleep:
    a. **Confirm the paste landed:** `herdr pane read "<pane_id>"` and check the input box shows the **tail** of `<request>` (the last few words before ` || `). Re-read a few times (short waits) until it appears.
    b. **Enter:** `herdr pane send-keys "<pane_id>" Enter`.
    c. **Verify it submitted:** read again — if the payload tail is STILL in the input box (unsent), press Enter once more. Repeat up to ~3 times.
    d. Submitted = the input box is empty / the agent flipped to `working` (the text has left the box). If it never submits after ~3 tries, report the stuck paste to the user rather than assuming it ran.

    (If herdr later exposes an atomic text-plus-Enter into a *running* TUI — `pane run` delivers both in one request but currently targets the shell to spawn the harness, not a live TUI — prefer that: it eliminates this inter-request race by construction.)
11. Report the tab label, pane ID, the caller pane the agent will call back to, and confirm the agent is running. Note that the callback is fire-and-forget (best-effort): if the spawned agent crashes before its final step the ping won't fire, so for critical work keep a fallback (ask, or check for the expected output file).

The user's request is the message they sent with this invocation, minus any harness-selection token consumed in step 1.
