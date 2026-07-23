---
name: thread
description: Use ONLY when the user explicitly asks to launch or spawn a new agent thread in a herdr tab. Spawns a new agent in a fresh herdr tab (or an isolated git-worktree workspace when the task involves branch work) — the harness (claude / opus / glm / ds / opencode / pi, or whatever is in the harness registry) is chosen from the user's message and launched in that harness's native auto/yolo mode. Runs the user's request inside it and wires a fire-and-forget callback so the spawned agent pings the caller's pane when it finishes. Requires running inside herdr.
---

Before using this skill, check that `HERDR_ENV=1`. If it is not set to `1`, tell the user you are not running inside a herdr-managed pane and stop. Do not attempt the steps below from outside herdr.

Verified against herdr 0.7.5 (2026-07-22). This skill requires herdr >= 0.7.5: it uses the agent CLI facade (`agent start`, `agent prompt`, `agent wait`) added in 0.7.5, which also REMOVED the old top-level `wait agent-status` command. If an `agent` subcommand errors as unknown, tell the user to update herdr (`herdr update` or `brew upgrade herdr`) and stop.

When invoked, execute these steps immediately without asking for confirmation:

1. **Select the harness and prepare `<request>`.** Read the registry at `harnesses.json` in **this skill's own directory** — the `Base directory for this skill:` path shown at the top of this skill (so it resolves for both global `~/.claude/skills/thread/` and project-level `.claude/skills/thread/` installs). If that file is missing or not valid JSON, fall back to this inline default and tell the user the config file was ignored:

   ```json
   { "default": "claude", "prompt_on_missing": true, "harnesses": [
     { "name": "claude",   "label": "Claude (Anthropic)", "command": "claude",   "kind": "claude",   "auto_flag": "--permission-mode auto" },
     { "name": "glm",      "label": "GLM (Z.ai)",         "command": "glm",      "kind": "claude",   "auto_flag": "--permission-mode auto" },
     { "name": "ds",       "label": "DeepSeek",           "command": "ds",       "kind": "claude",   "auto_flag": "--permission-mode auto" },
     { "name": "opencode", "label": "OpenCode",           "command": "opencode", "kind": "opencode", "auto_flag": "--auto" },
     { "name": "pi",       "label": "Pi",                 "command": "pi",       "kind": "pi",       "auto_flag": "--approve" }
   ] }
   ```

   `kind` is the herdr agent kind of the TUI the command ultimately runs (`herdr agent start --help` lists valid kinds). An entry whose `command` equals its `kind` is a **canonical** harness (launchable via `herdr agent start`); an entry whose `command` differs (glm, ds — wrappers around claude) is a **wrapper** and takes the fallback launch path in step 7. If an entry lacks `kind`, treat it as a wrapper with unknown kind.

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

   Call the selected entry's `command` value `<command>`, its `auto_flag` value `<auto_flag>`, and its `kind` value `<kind>`.

2. Derive a short, descriptive tab label from `<request>` (max 30 chars, kebab-case or title case).

3. Capture YOUR OWN pane id so the spawned agent can call back. Get it LIVE from herdr — do NOT trust `$HERDR_PANE_ID`, which is set at shell startup and goes stale after a pane move (a stale id would send the finish-callback to a dead pane): `herdr pane current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])'`. Call this `<caller_pane>`. If it's empty (not running inside herdr — should not happen given the check above, but guard anyway), skip the callback wiring in step 8 and just note that to the user.

4. **Decide isolation: plain tab or git worktree.** If `<request>` implies branch work — creating or switching branches, committing a feature, "on its own branch", "in a worktree", parallel edits to a repo the caller is also working in — use a worktree (step 5b). A same-cwd spawn that runs `git checkout -b` yanks the CALLER off their branch mid-session; the worktree path exists precisely to prevent that. Otherwise use a plain tab (step 5a). If genuinely ambiguous, prefer the plain tab but say so in the report.

5. Create the pane the agent will run in:
   a. **Plain tab:** find the current workspace ID from `herdr workspace list` (the focused one, or workspace 3 if there's a "Vox" workspace), then `herdr tab create --workspace <N> --label "<label>"`. For a **wrapper** harness, add `--env HERDR_AGENT=<kind>` so herdr's agent detection uses the underlying agent's screen manifest even though the visible command is the wrapper.
   b. **Worktree:** `herdr worktree create --branch "<type/kebab-topic>" --label "<label>"` run from (or with `--cwd`) the repo the task concerns; add `--base <ref>` when the branch should start from something other than the current HEAD. This creates the git worktree AND a new herdr workspace with a tab whose root pane starts in the worktree checkout. (There is no `--env` here; for a wrapper harness just proceed — detection still normalizes the claude TUI, it may only take a moment longer.)

6. Parse the root pane ID from the JSON response — field `result.root_pane.pane_id` for both tab create and worktree create. Call this `<pane_id>`. Also note the new pane's `cwd` (for worktrees, `result.worktree.path`) — if it differs from the directory the task concerns, pass ABSOLUTE paths in the request so the agent can find files regardless of its working directory. For the worktree path, DO tell the agent its checkout path and branch in the request.

7. Launch the harness and wait for readiness:
   - **Canonical harness** (`command` == `kind`): one command does both — `herdr agent start "<label-slug>" --kind <kind> --pane "<pane_id>" -- <auto_flag words>` (native args go after `--`, e.g. `-- --model opus --permission-mode auto`). It returns success only once the agent TUI is detected and ready for input (default timeout 30s; raise with `--timeout <ms>` up to 300000). The name must be unique among live agents — on a name-conflict error, retry once with a numeric suffix.
   - **Wrapper harness** (`command` != `kind`, e.g. glm, ds): `herdr pane run "<pane_id>" "<command> <auto_flag>"`, then wait for readiness: `herdr agent wait "<pane_id>" --until idle --timeout 60000`. (`agent wait` returns `agent_not_running` promptly if the pane dies.)

   **Then dismiss startup dialogs before prompting:** `herdr pane read "<pane_id>" --source visible --lines 20`. If it shows claude's folder-trust dialog ("Do you trust the files in this folder?"), `herdr pane send-keys "<pane_id>" Enter` to accept and re-read; claude blocks on this in any directory it has not seen before (fresh dated dirs, scratchpads, and ALWAYS a new worktree checkout), `agent start` can report ready while the dialog is up, and a prompt sent against it stalls. If it shows "new MCP servers found", `herdr pane send-keys "<pane_id>" Esc` and re-read.

   If the launch or wait fails, read the pane (`herdr pane read "<pane_id>"`). If the output shows a shell error (`command not found`, crash/stack trace), report the launch failure to the user and stop. If it shows a TUI that simply wasn't status-detected, wait ~5s more and proceed to step 8 anyway — a prompt to a ready TUI is harmless.

   Do NOT use `agent wait` to detect *completion* later: terminal statuses vary by harness (pi ends `done`, opencode has been observed stuck at `working` after finishing). Completion is signaled only by the callback in step 8.

8. **Submit the request atomically with `agent prompt`.** This replaces the old send-text / poll / Enter dance: `agent prompt` honors live bracketed-paste mode before sending Enter, so the "text sits in the input box, never sent" race is gone by construction. Keep the whole payload on ONE line (simplest quoting; use a ` || ` sentinel instead of a blank line) and single-quote the callback so nothing needs escaping inside the double-quoted payload:

   `herdr agent prompt "<pane_id>" "<request>  ||  WHEN YOU FINISH: notify the requesting agent so a message lands in their pane — run  herdr agent prompt '<caller_pane>' 'THREAD COMPLETE: <one-line summary incl. any file path>'  and optionally  herdr notification show 'Thread done: <label>' --sound done" --wait --until working --timeout 15000`

   (Omit the callback clause if `<caller_pane>` was empty in step 3.)

   The `--wait --until working` confirms the submission actually took: the server requires an observed state change within 5s of submission, else it returns `agent_prompt_stalled`. On `agent_prompt_stalled` or timeout, fall back: read the pane; if the payload tail is visibly stuck in the input box, `herdr pane send-keys "<pane_id>" Enter` and re-read (up to ~3 times); if it never submits, report the stuck prompt to the user rather than assuming it ran. If the agent was ALREADY `working` when you prompted (shouldn't happen right after launch), treat the wait result as unreliable and verify by reading the pane.

9. Report the tab (or worktree workspace + branch + checkout path) label, pane ID, the caller pane the agent will call back to, and confirm the agent is running. Note that the callback is fire-and-forget (best-effort): if the spawned agent crashes before its final step the ping won't fire, so for critical work keep a fallback (ask, or check for the expected output file). For a worktree thread, mention that when the work is merged the worktree can be cleaned up with `herdr worktree remove --workspace <workspace_id>` (the branch itself survives in the source repo).

The user's request is the message they sent with this invocation, minus any harness-selection token consumed in step 1.
