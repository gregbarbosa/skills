---
name: advise
description: Use when project work is growing complex or splitting into independent strands that could progress in parallel across separate sessions, such as several related projects moving toward one goal, or a single effort branching into pieces that don't depend on each other. This skill SURFACES the option to orchestrate and ALWAYS offers and agrees scope with the user before spawning anything. On agreement it spins up one herdr worker pane per project on a shared theme plus a Fable advisor pane that watches and nudges them, while the user can jump into any pane. Requires running inside herdr.
---

Before anything else, check that `HERDR_ENV=1`. If it is not `1`, tell the user this skill needs to run inside a herdr-managed pane and stop.

## Two phases: never skip Phase A

This skill has two phases. You MUST NOT begin Phase B until the user has explicitly agreed to a scope in Phase A.

- **Phase A, offer & agree (no spawning).** Recognize that the work could fan out, offer it, propose a scope, and discuss until the user agrees.
- **Phase B, spawn & advise.** Only after explicit agreement: spin up the room and hand off to the Fable advisor.

If you arrived here because the skill surfaced on its own (the work looked parallelizable), you are in Phase A. Offering is not spawning.

## Phase A: offer & agree

1. **Offer.** In one or two sentences, name the independent strands you see and offer to run them in parallel sessions while you keep talking in this conversation. Example: "This is splitting into three independent pieces. I can spin up a session per piece and advise them while we stay here. Want to?"
2. **Propose scope.** Map the goal to concrete projects using, in order:
   - `PROJECTS.md` at the workspace root (canonical project registry).
   - Open herdr workspaces/panes: `herdr workspace list`, `herdr pane list` (work already in flight, with cwds/branches).
   - Dated `tries/` subdirectories and branches whose names match the goal.
   - Memory (`MEMORY.md` pointers) for project relationships.
   Present the proposed roster as a short list: each project, its path/branch, and the one job that worker will own.
3. **Discuss.** Refine with the user: add or drop projects, adjust each worker's job. Do not spawn during this phase.
4. **Get an explicit go**, then proceed to Phase B.

## Phase B: spawn the room

1. **Finalize the roster:** a list of `{ project_name, abs_path, branch, worker_task }`, plus the shared `theme` (one line).
2. **Read config** from `advise.json` in THIS skill's directory (the `Base directory for this skill:` path shown at the top). Fields: `worker.command`, `worker.model_flag`, `advisor.command`, `advisor.model_flag`, `layout_threshold`. If it is missing or not valid JSON, use this inline default and tell the user:

   ```json
   { "worker": {"command":"claude","model_flag":"--model sonnet"}, "advisor": {"command":"claude","model_flag":"--model fable"}, "layout_threshold": 3 }
   ```

   For a per-worker harness override the user named, resolve its `command` and `auto_flag` from `harnesses.json` in the `thread` skill's directory if present; otherwise keep the default worker.
3. **Find the current workspace id:** `herdr workspace list` gives the focused workspace's `workspace_id`.
4. **Create the room and choose layout** by roster size N vs `layout_threshold`. Create one new workspace for the room either way: `herdr workspace create --label "<short theme>"`; parse `result.root_pane.pane_id` (this is the advisor pane) and `result.workspace`.
   - **N ≤ threshold (side-by-side panes):** for each worker, split from the previous pane: `herdr pane split "<prev_pane>" --direction right --no-focus`; parse `result.pane.pane_id`.
   - **N > threshold (one tab per worker):** for each worker, `herdr tab create --workspace <ws> --label "<project>"`; parse `result.root_pane.pane_id`.
5. **Launch each worker** in its pane:
   - `herdr pane run "<pane_id>" "cd <abs_path> && <worker.command> <worker.model_flag> --permission-mode auto"`. For a non-claude override, use that harness's `auto_flag` in place of `<model_flag> --permission-mode auto`.
   - Wait for readiness: `herdr wait agent-status "<pane_id>" --status idle --timeout 60000`.
   - **Dismiss the MCP-enable prompt:** `herdr pane read "<pane_id>" --source visible --lines 20`; if it contains "new MCP servers found", run `herdr pane send-keys "<pane_id>" Esc`, then re-read to confirm it cleared.
   - Send the worker its task: `herdr pane run "<pane_id>" "<worker_task>. Scope and read first; flag any irreversible change before making it."`
   - Record `project` to `pane_id`.
6. **Prime the advisor pane** (Fable):
   - `herdr pane run "<advisor_pane>" "<advisor.command> <advisor.model_flag> --permission-mode auto"`; `herdr wait agent-status "<advisor_pane>" --status idle --timeout 60000`; dismiss any MCP prompt as above.
   - Send the priming brief: `herdr pane send-text "<advisor_pane>" "<brief>"` then `herdr pane send-keys "<advisor_pane>" Enter`. The brief MUST include the theme, the roster as `project` to `pane_id`, and the advisor operating rules below.
7. **Announce** in one line which workers are up and that the Fable advisor now holds the room, e.g. "Room up: 3 Sonnet workers (A, B, C) plus Fable advisor in workspace N. Jump into any pane; talk to the advisor pane to steer."

## Advisor operating rules (include verbatim in the priming brief)

You are the Fable advisor for this room. Workers: `<roster>`. Theme: `<theme>`.
- Run ONE assessment pass now: for each worker pane, `herdr pane read <pane_id> --source recent --lines 40`, judge progress against the theme, and post a short roll-up in THIS pane (who is doing what, who is stuck).
- Only NUDGE a worker whose `agent_status` (from `herdr pane list`) is `idle`, `blocked`, or `done`, never while `working`. To nudge: `herdr pane send-text <pane_id> "<one concrete instruction>"` then `herdr pane send-keys <pane_id> Enter`. Echo each nudge in this pane so the user sees who said what.
- Re-read pane ids from `herdr pane list` each pass; ids compact when panes close, so never cache them.
- After the initial pass, WAIT for the user. Do not loop continuously. Act when the user asks you to check in, or tells you to nudge or re-scope a worker. The user may later put you on an interval with /loop.

## Teardown

When the user is done, close the room: `herdr workspace close <ws>` (or close panes/tabs individually with `herdr pane close` / `herdr tab close`). Confirm before closing if any worker is still `working`.
