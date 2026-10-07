---
name: field-handler
description: Run a room of parallel field agents on one theme and steer them from this session. Use when work splits into independent strands that could progress in parallel, such as several projects moving toward one goal. Surfaces the option and agrees scope with the user before spawning anything. Requires a herdr pane.
argument-hint: "<theme or goal>"
---

# field-handler: run a room of field agents

Check that `HERDR_ENV=1`. If it is not, tell the user you do not run inside a
herdr pane, then stop.

`${CLAUDE_SKILL_DIR}` is this skill's directory (outside Claude Code, the
directory this SKILL.md sits in); it holds `handler.json`. `<agent_dir>` is
the sibling `field-agent` directory, holding `field.py`, `harnesses.json` and
`dispatch.md`:

```bash
ls ${CLAUDE_SKILL_DIR}/../field-agent/field.py
```

If that fails, look with `find ~/.claude ~/.agents -maxdepth 5 -type d -path
'*skills/field-agent' 2>/dev/null`. If both fail, the suite is not installed:
tell the user to run `npx skills add gregbarbosa/skills -s '*' -g -y`, then stop.

**This session is the handler.** Each agent you start is a field agent. You
agree the scope, dispatch, record, watch and triage; the watching stays here.
Field agents report by prompting you, so their reports arrive as turns in this
session beside the user's messages.

## After a compaction, or when an event lands

Run `python3 <agent_dir>/field.py status` before you ask the user anything.
The ledger is the memory: your context gets summarised, the file does not. If
no `Monitor` runs the watch loop (a herdr server restart stops it), arm it
again (Phase B step 0) and run `field.py catchup` once.

### Triage

**Triage only your roster.** The ledger and the watch loop are global to this
machine, so events also name agents from the user's other sessions; tell the
user in one line and leave those panes alone. A prompt to a stranger's idle
agent injects work into a session you know nothing about.

Read the work first: `herdr agent read "<agent_name>" --source recent --lines 80`.

| Event | What you do |
|-------|-------------|
| `COMPLETE` / `[FIELD] DONE` | Verify the claim against the files it names; run the build or the tests when it touched code. Do not trust the summary. Tell the user the verdict and send a `PushNotification` (the agent already raised the desktop notification). |
| `[FIELD] BLOCKED` | Read the pane. Answer it yourself when the brief makes the answer unambiguous. Escalate only a decision that is genuinely the user's. |
| `[FIELD] IDLE` | It stopped without a report. Read its checklist in `~/.claude/field/checklists/<agent_name>.md`: an unticked item is open work, whatever the last message says. Finished quietly: triage as done. Work open, no blocker stated: prompt "Still open: <items>. Continue. If one is blocked, report BLOCKED and say what blocks it." After two or three nudges on the same task, tell the user it is stuck. |
| `[FIELD] GONE` | The pane closed unread. Check the branch and the files, then report what was lost. |
| `MILESTONE` / `START` | Note it. Reply only to correct the agent. |

Then, for a settled agent:

1. **Queued follow-up.** If `status` shows `queued:` under the agent, dispatch
   it now without waiting for the user (a fresh field agent for a new task, or
   `herdr agent prompt "<agent_name>" "<follow-up>"` to continue the same one),
   then clear it: `python3 <agent_dir>/field.py queue "<agent_name>" --done`.
   `field-audit` refuses to close an agent that still holds one.
2. **Acknowledge**:
   `python3 <agent_dir>/field.py ack "<agent_name>" "<verdict; files; test result>"`

### Standing duties

- **Address agents by name:** `herdr agent prompt <agent_name> "<one concrete
  instruction>"`. A prompt to a `working` agent queues behind its current turn.
- **Wait between events.** Act when an agent reports, a `[FIELD]` event lands,
  or the user asks. `herdr agent wait` blocks your turn; keep it for a short,
  known wait during a launch.
- **Text in an agent's input box** is usually Claude Code's prompt suggestion,
  not a stuck submission. Leave it.

### Teardown

The room closes through the audit, never on your own judgment: an unread pane
holds work nothing else records.

1. Run the **`field-audit`** skill. It reads, verifies, and closes only the
   panes that are provably finished. It clears a moved worktree checkout with
   `git worktree remove <path>` once the branch is merged or the user says so.
2. Confirm with the user before you close a pane whose agent is `working`.
3. Close the room tab with `herdr tab close <tab_id>`. The user's workspace
   stays open.

## Phase A: offer and agree (spawn nothing)

If this skill surfaced on its own, you are here.

1. **Offer.** In one or two sentences, name the independent strands and offer
   to run them in parallel panes you steer.
2. **Propose a roster** from, in order: `python3 <agent_dir>/field.py status`
   (work already dispatched); `herdr agent list` and `herdr workspace list`
   (each agent's `terminal_title_stripped` says what it does now); branches and
   dated directories matching the goal; the agent brain. List each project, its
   path and branch, and the one job its field agent owns.
3. **Discuss.** Add or drop projects, adjust each job.
4. **Get an explicit go.** Then Phase B.

## Phase B: open the room

Read the **`herdr`** skill and run `herdr --skill` first.

### Step 0: Claim your name and arm the watch loop

```bash
herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])'
herdr agent list | python3 -c 'import sys,json;print([a.get("name") for a in json.load(sys.stdin)["result"]["agents"]])'
herdr agent rename "<self_pane>" m
```

If a live agent holds `m`, use `m-<short-theme>` everywhere. Read the pane id
live (`$HERDR_PANE_ID` goes stale after a move). Then, before you spawn:

```
Monitor(
  description: "herdr field agents reaching done/idle/blocked",
  persistent: true,
  command: "FIELD_HANDLER_PANE=<self_pane> python3 <agent_dir>/field.py watch --interval 15"
)
```

One watch loop per machine; if `field-agent` already armed one, keep it. Run
`python3 <agent_dir>/field.py catchup` once.

### Step 1: Finalize the roster

A list of `{ project_name, agent_name, abs_path, branch, task }` plus the
shared one-line `theme`. `agent_name` is a kebab slug matching
`[a-z][a-z0-9_-]{0,31}`, under 24 characters, unique among live agents.

### Step 2: Read the config

`${CLAUDE_SKILL_DIR}/handler.json`: `agent.command`, `agent.model_flag`,
`model_floor`, `layout_threshold`. If it is missing or invalid, tell the user
and use `{"agent":{"command":"claude","model_flag":"--model sonnet"},"model_floor":"sonnet","layout_threshold":4}`.

**`model_floor` is Sonnet:** Haiku 4.5 ignores `--permission-mode auto` and
stops at its first tool call. If the user asks for Haiku, say so and let them
decide. For a per-agent harness the user named, read `command`, `kind`,
`auto_flag` and `brief_format` from `<agent_dir>/harnesses.json`; `command`
equal to `kind` is canonical, otherwise a wrapper.

### Step 3: Decide isolation per agent

An agent needs a worktree when BOTH hold: another roster entry shares its repo
(or its branch differs from that checkout's), and it will commit or change
branch. A shared-checkout agent that runs `git checkout -b` switches every
session in that directory, this one included. Read-only agents in one repo
need no worktree; say in their task that they leave git alone.

### Step 4: Create the room in the current workspace

```bash
WS=$(herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["workspace_id"])')
```

**N <= `layout_threshold`: one tab, one pane per agent.** The tab's root pane
is agent 1:

```bash
herdr tab create --workspace "$WS" --label "field agents" --cwd "<abs_path_1>" --no-focus
```

Parse `.result.tab.tab_id` and `.result.root_pane.pane_id`, then split a wide
pane right and a tall one down (parse `.result.pane.pane_id` from each):

| Agent | Split |
|-------|-------|
| 2 | `herdr pane split "<pane_1>" --direction right --cwd "<abs_path_2>" --no-focus` |
| 3 | `herdr pane split "<pane_1>" --direction down --cwd "<abs_path_3>" --no-focus` |
| 4 | `herdr pane split "<pane_2>" --direction down --cwd "<abs_path_4>" --no-focus` |

**N > `layout_threshold`: one tab per agent, still in `$WS`:**
`herdr tab create --workspace "$WS" --label "<project>" --cwd "<abs_path>" --no-focus`.

**Worktree agents.** `worktree create` always opens its own workspace, so
create the checkout, then move its root pane into the room:

```bash
herdr worktree create --cwd "<repo>" --branch "<branch>" --label "<project>" --no-focus
herdr pane move "<root_pane>" --tab "<tab_id>" --split <right|down> --target-pane "<pane_n>" --no-focus
```

Above the threshold use `--new-tab --workspace "$WS" --label "<project>"`
instead. The move gives the pane a NEW id (`.result.move_result.pane.pane_id`);
use it from here on. Put absolute paths (`.result.worktree.path`) in that
agent's task.

### Steps 5 and 6: Launch, register, brief

Read `<agent_dir>/dispatch.md` now and follow it for every agent: launch with
`handler.json`'s `model_flag`, clear the dialogs, check the permission mode,
and register each one. Launch and register every agent before you brief any,
then brief each with `field.py brief --scoped`.

### Step 7: Announce, then work the room

In one line: which agents are up, their models, the tab that holds them, which
work in a worktree (branch and path), and that the watch loop is armed. Tell the
user this thread will now share turns with the agents' reports, and offer
`/loop` for hands-off running.

Then run one assessment pass: `herdr agent list` against the roster. A roster
agent missing from the list is not gone (detection lags on a fresh worktree
pane); `herdr pane read` its pane. Read only agents that look stuck, off-theme
or missing (`herdr agent read <agent_name> --source recent-unwrapped --lines
40`) and give the user a short roll-up.

## Failure modes

| Symptom | Fix |
|---------|-----|
| A `COMPLETE` never arrives | The agent crashed; the watch loop reports `GONE` or `IDLE`. Read the pane. |
| Duplicate `[FIELD]` lines | Two watch loops. Stop the second `Monitor`. |
| The room finished hours ago, unread | No watch loop. Arm it (step 0), run `catchup`. |
| `agent start` returns `agent_not_ready` | A startup dialog. The name still works; clear it (`dispatch.md`). |
| `agent list` shows an unnamed agent | A wrapper launched without a rename: `herdr agent rename <pane> <name>`, then register it. |
| `field-audit` refuses a close: queued follow-up | Dispatch it, then `field.py queue "<agent_name>" --done`. |
