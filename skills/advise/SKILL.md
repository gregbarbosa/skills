---
name: advise
description: Use when project work is growing complex or splitting into independent strands that could progress in parallel across separate sessions, such as several related projects moving toward one goal, or a single effort branching into pieces that don't depend on each other. This skill SURFACES the option to orchestrate and ALWAYS offers and agrees scope with the user before spawning anything. On agreement it spins up one herdr worker pane per project on a shared theme plus a Fable advisor pane that watches and nudges them, while the user can jump into any pane. Requires running inside herdr.
---

Before anything else, check that `HERDR_ENV=1`. If it is not `1`, tell the user this skill needs to run inside a herdr-managed pane and stop.

Verified against herdr 0.7.5 (2026-07-23). This skill requires herdr >= 0.7.5: it uses the agent CLI facade (`agent start`, `agent prompt`, `agent wait`, `agent list`) added in 0.7.5. If an `agent` subcommand errors as unknown, tell the user to update herdr (`herdr update` or `brew upgrade herdr`) and stop.

## Two phases: never skip Phase A

This skill has two phases. You MUST NOT begin Phase B until the user has explicitly agreed to a scope in Phase A.

- **Phase A, offer & agree (no spawning).** Recognize that the work could fan out, offer it, propose a scope, and discuss until the user agrees.
- **Phase B, spawn & advise.** Only after explicit agreement: spin up the room and hand off to the Fable advisor.

If you arrived here because the skill surfaced on its own (the work looked parallelizable), you are in Phase A. Offering is not spawning.

## Phase A: offer & agree

1. **Offer.** In one or two sentences, name the independent strands you see and offer to run them in parallel sessions while you keep talking in this conversation. Example: "This is splitting into three independent pieces. I can spin up a session per piece and advise them while we stay here. Want to?"
2. **Propose scope.** Map the goal to concrete projects using, in order:
   - `PROJECTS.md` at the workspace root (canonical project registry).
   - Live agents and panes: `herdr agent list`, `herdr workspace list` (work already in flight, with cwds/branches).
   - Dated `tries/` subdirectories and branches whose names match the goal.
   - Memory (`MEMORY.md` pointers) for project relationships.
   Present the proposed roster as a short list: each project, its path/branch, and the one job that worker will own.
3. **Discuss.** Refine with the user: add or drop projects, adjust each worker's job. Do not spawn during this phase.
4. **Get an explicit go**, then proceed to Phase B.

## Phase B: spawn the room

1. **Finalize the roster:** a list of `{ project_name, agent_name, abs_path, branch, worker_task }`, plus the shared `theme` (one line). `agent_name` is a short kebab slug of the project (herdr agent names must be unique among live agents; on a name-conflict error at launch, retry once with a numeric suffix). Also derive `<advisor_name>` as `<short-theme-slug>-advisor`.
2. **Read config** from `advise.json` in THIS skill's directory (the `Base directory for this skill:` path shown at the top). Fields: `worker.command`, `worker.model_flag`, `advisor.command`, `advisor.model_flag`, `layout_threshold`. If it is missing or not valid JSON, use this inline default and tell the user:

   ```json
   { "worker": {"command":"claude","model_flag":"--model sonnet"}, "advisor": {"command":"claude","model_flag":"--model fable"}, "layout_threshold": 3 }
   ```

   For a per-worker harness override the user named, resolve its `command`, `kind`, and `auto_flag` from `harnesses.json` in the `thread` skill's directory if present; otherwise keep the default worker. An entry whose `command` equals its `kind` launches via `agent start` like the defaults; a wrapper entry (`command` != `kind`, e.g. glm, ds) takes the wrapper path noted in step 5.
3. **Decide isolation per worker.** A worker needs a git worktree when another roster entry shares its repo, or when its `branch` differs from what that checkout currently has. A shared-checkout worker that runs `git checkout -b` switches every other session in that directory, including this one; the worktree path exists to prevent that. Workers in distinct directories on their current branches stay in the room workspace.
4. **Create the room.** One new workspace either way: `herdr workspace create --label "<short theme>"`; parse `result.root_pane.pane_id` (this is `<advisor_pane>`) and `result.workspace`. Then create each worker's pane:
   - **Room workers, N ≤ `layout_threshold` (side-by-side panes):** split from the previous pane with the worker's own directory: `herdr pane split "<prev_pane>" --direction right --cwd "<abs_path>" --no-focus`; parse `result.pane.pane_id`.
   - **Room workers, N > threshold (one tab per worker):** `herdr tab create --workspace <ws> --label "<project>" --cwd "<abs_path>"`; parse `result.root_pane.pane_id`.
   - **Worktree workers:** `herdr worktree create --cwd "<repo>" --branch "<branch>" --label "<project>"`. This creates the git worktree AND its own workspace; parse `result.root_pane.pane_id` and note `result.worktree.path`. These workers live outside the room workspace; record that in the roster and tell the worker its checkout path and branch in its task.
5. **Launch the advisor first** (so it exists before any worker can finish and call back):
   - `herdr agent start "<advisor_name>" --kind claude --pane "<advisor_pane>" -- <advisor.model_flag words> --permission-mode auto`. It returns once the TUI is ready (default timeout 30s; raise with `--timeout <ms>` if needed).
   - **Dismiss the MCP-enable prompt:** `herdr pane read "<advisor_pane>" --source visible --lines 20`; if it contains "new MCP servers found", `herdr pane send-keys "<advisor_pane>" Esc`, then re-read to confirm it cleared.
   - Send the priming brief atomically: `herdr agent prompt "<advisor_name>" "<brief>" --wait --until working --timeout 15000`. The brief MUST include the theme, the roster as `project` / `agent_name` / `pane_id` (worktree workers flagged with their checkout path), and the advisor operating rules below. On `agent_prompt_stalled` or timeout, read the pane; if the text is stuck in the input box, `herdr pane send-keys "<advisor_pane>" Enter` and re-read (up to ~3 times) before reporting a stuck prompt.
6. **Launch each worker** in its pane:
   - Default and canonical-override workers: `herdr agent start "<agent_name>" --kind <kind> --pane "<pane_id>" -- <model_flag words> --permission-mode auto` (for an override, its native args are its `auto_flag`). Wrapper-harness workers instead: `herdr pane run "<pane_id>" "<command> <auto_flag>"` then `herdr agent wait "<pane_id>" --until idle --timeout 60000`.
   - Dismiss the MCP-enable prompt as in step 5.
   - Send the task with the finish callback wired in, one line, ` || ` as separator: `herdr agent prompt "<agent_name>" "<worker_task>. Scope and read first; flag any irreversible change before making it.  ||  WHEN YOU FINISH: run  herdr agent prompt '<advisor_pane>' 'WORKER DONE: <project>: <one-line summary incl. any file path>'" --wait --until working --timeout 15000`. Same stuck-prompt fallback as step 5.
7. **Announce** in one line which workers are up and that the Fable advisor now holds the room, e.g. "Room up: 3 Sonnet workers (A, B, C) plus Fable advisor in workspace N; worker C is in its own worktree workspace. Jump into any pane; talk to the advisor pane to steer."

## Advisor operating rules (include verbatim in the priming brief)

You are the Fable advisor for this room. Workers: `<roster>`. Theme: `<theme>`.
- Run ONE assessment pass now: `herdr agent list` gives every worker's `agent_status` and live `terminal_title` (the title describes what that agent is currently doing). Triage from that first; only `herdr pane read <pane_id> --source recent --lines 40` the workers that look stuck or off-theme. Post a short roll-up in THIS pane (who is doing what, who is stuck).
- Address workers by their agent NAME (from the roster), not by cached pane ids: `herdr agent prompt <agent_name> "<one concrete instruction>"`. Names are stable for the life of the agent; pane ids are not.
- Only NUDGE a worker whose `agent_status` is `idle`, `blocked`, or `done`, NEVER while `working`: `agent prompt` will inject into a running turn. Echo each nudge in this pane so the user sees who said what.
- Workers will report completion into this pane as `WORKER DONE: <project>: <summary>` messages. When one arrives, verify the claim against that worker's pane if it matters, update your roll-up, and tell the user.
- After the initial pass, WAIT for the user or for WORKER DONE messages. Do not loop continuously. Act when a worker reports done, when the user asks you to check in, or when told to nudge or re-scope a worker. The user may later put you on an interval with /loop.

## Teardown

When the user is done, close the room: `herdr workspace close <ws>` (or close panes/tabs individually with `herdr pane close` / `herdr tab close`). Worktree workers have their own workspaces: once their work is merged, `herdr worktree remove <workspace_id>` cleans up both the workspace and the checkout. Confirm before closing if any worker is still `working`.
