---
name: field-agent
description: Dispatch one field agent (claude, glm, ds, opencode or pi) into a herdr tab or worktree with a reporting contract, a ledger record and a watch loop. Use when the user asks to launch, spawn, dispatch or hand off work to another agent. Several agents on one theme is field-handler. Requires a herdr pane.
argument-hint: "[--harness <name>] <task>"
---

# field-agent: dispatch a field agent and keep it

Check that `HERDR_ENV=1`. If it is not, tell the user you do not run inside a
herdr pane, then stop.

`${CLAUDE_SKILL_DIR}` below is this skill's directory (outside Claude Code,
use the directory this SKILL.md sits in). It holds `field.py`, the ledger tool
(state in `~/.claude/field/`), `harnesses.json`, and `dispatch.md`.

You are the **handler**; each agent you start is a **field agent**. A handler
dispatches with a brief, records the agent in the ledger, watches the roster,
and triages every report. Skip any of the four and finished work goes unread.

## After a compaction, or when an event lands

Run `python3 ${CLAUDE_SKILL_DIR}/field.py status` before you ask the user
anything. The ledger is the memory: your context gets summarised, the file does
not. If no `Monitor` runs the watch loop (a herdr server restart stops it), arm
it again (step 2) and run `field.py catchup` once.

### Triage

A `[FIELD]` event or a `FIELD REPORT` message re-invokes you. Read the work
first:

```bash
herdr agent read "<name>" --source recent --lines 80
```

| Event | What you do |
|-------|-------------|
| `COMPLETE` / `[FIELD] DONE` | Verify the claim against the files it names; run the build or the tests when it touched code. Do not trust the summary. Tell the user the verdict and send a `PushNotification` (the agent already raised the desktop notification). |
| `[FIELD] BLOCKED` | Read the pane. Answer it yourself when the brief makes the answer unambiguous: `herdr agent prompt "<name>" "<answer>"`. Escalate only a decision that is genuinely the user's. |
| `[FIELD] IDLE` | It stopped without a report. Read its checklist in `~/.claude/field/checklists/<name>.md`: an unticked item is open work, whatever the last message says. Finished quietly: triage as complete. Work open, no blocker stated: prompt "Still open: <items>. Continue. If one is blocked, report BLOCKED and say what blocks it." After two or three nudges on the same task, tell the user it is stuck. |
| `[FIELD] GONE` | The pane closed unread. Check the branch and the files, then tell the user what was lost. |
| `MILESTONE` / `START` | Note it. Reply only to correct the agent. |

Then, for a settled agent:

1. **Queued follow-up.** If `status` shows `queued:` under the agent, dispatch
   it now without waiting for the user (a fresh field agent for a new task, or
   `herdr agent prompt "<name>" "<follow-up>"` to continue the same one), then
   clear it: `python3 ${CLAUDE_SKILL_DIR}/field.py queue "<name>" --done`.
   `field-audit` refuses to close an agent that still holds one.
2. **Acknowledge**, which stops the event resurfacing:
   `python3 ${CLAUDE_SKILL_DIR}/field.py ack "<name>" "<verdict; files; test result>"`

The ledger and the watch loop are global to this machine, so events also name
agents another handler dispatched. Tell the user in one line and leave them be.

### Standing duties

- **Supervise through the watch loop.** `herdr agent wait` blocks your turn;
  keep it for a short, known wait during a launch. Asking an agent whether it
  is done wastes its turn and yours.
- **Address agents by name, never by pane id.** A pane id changes when the
  pane moves and resolves to nothing once it closes.
- **Tidy up with `field-audit`.** It reads each result, verifies it, and closes
  only panes that are provably finished.

## Dispatch

Read the **`herdr`** skill and run `herdr --skill` before your first dispatch.

### Step 1: Claim your handler name (once per session)

```bash
SELF=$(herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr agent rename "$SELF" m
```

If a live agent already holds `m`, use `m-<short-topic>` everywhere. Read the
pane id live; `$HERDR_PANE_ID` goes stale after a pane move.

### Step 2: Arm the watch loop (once per session)

```
Monitor(
  description: "herdr field agents reaching done/idle/blocked",
  persistent: true,
  command: "FIELD_HANDLER_PANE=<self_pane> python3 ${CLAUDE_SKILL_DIR}/field.py watch --interval 15"
)
```

One watch loop per machine; two print every event twice. It prints one line
per status change and stays quiet otherwise:

```
[FIELD] DONE | name=parser-fix | pane=w15:p7 | harness=claude | was=working | task=fix the overflow in SleepParser
```

Run `python3 ${CLAUDE_SKILL_DIR}/field.py catchup` once, for agents that
settled before the loop was armed.

### Step 3: Choose the harness and build the request

Read `${CLAUDE_SKILL_DIR}/harnesses.json` (`default`, `prompt_on_missing`, and
per harness `name`, `label`, `command`, `kind`, `auto_flag`, `brief_format`).
If it is missing or invalid, tell the user and use claude:
`command: claude, kind: claude, auto_flag: --permission-mode auto`.

An entry whose `command` equals its `kind` is **canonical**; one whose
`command` differs (glm, ds) is a **wrapper**. `dispatch.md` launches each.

Detect the harness from the user's message:

- `--harness <name>` or `-h <name>` at the start: select it, remove both words.
- The first word equals a registry `name`: select it, remove that word.
- Neither: keep the whole message. If `prompt_on_missing`, show a numbered
  menu of labels (blank selects `default`); otherwise use `default` silently.

The rest of the message is `<request>`.

**Sonnet is the model floor.** Haiku 4.5 ignores `--permission-mode auto` and
stops at its first tool call. If the user asks for Haiku, say so and let them
decide.

### Step 4: Name the agent and open its pane

`<name>`: kebab-case from the task, at most 24 characters, unique among live
agents (`herdr agent list`). Examples: `parser-overflow`, `qring-teardown`.

**Worktree** when `<request>` implies branch work (creates a branch, commits,
"on its own branch", or edits a repo you also edit: an agent in your directory
that runs `git checkout -b` moves your branch). Otherwise a **plain tab**; when
in doubt, a plain tab, and say so.

```bash
WS=$(herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["workspace_id"])')
# plain tab, beside you
herdr tab create --workspace "$WS" --label "<name>" --cwd "<cwd>" --no-focus
# worktree, from the repo the task concerns (or pass --cwd)
herdr worktree create --branch "<type>/<kebab-topic>" --label "<name>" --base <ref> --no-focus
```

Read `.result.root_pane.pane_id` as `<pane_id>`; for a worktree also
`.result.worktree.path`, and put absolute paths in the brief. A worktree opens
in its own workspace; to keep the agent beside you, move it and continue with
`.result.move_result.pane.pane_id`:

```bash
herdr pane move "<pane_id>" --new-tab --workspace "$WS" --label "<name>" --no-focus
```

### Steps 5 to 7: Launch, register, brief

Read `${CLAUDE_SKILL_DIR}/dispatch.md` now and follow it: launch the harness,
clear the startup dialogs, check the permission mode, register the agent, then
send the brief with `field.py brief`. Queue a follow-up at any point with
`python3 ${CLAUDE_SKILL_DIR}/field.py queue "<name>" "<follow-up>"`.

### Step 8: Report the dispatch

State the agent's name, pane, harness, workspace and branch for a worktree,
and the checkout path. Confirm the watch loop is armed.

For a worktree left in its own workspace: `herdr worktree remove --workspace
<wN>` cleans it after a merge and must run before the agent's pane closes. For
a moved worktree, or once the workspace is gone, only `git worktree remove
<path>` clears the checkout. The branch stays either way.

## Failure modes

| Symptom | Fix |
|---------|-----|
| A callback never arrives | The agent crashed; the watch loop reports `GONE` or `IDLE`. Read the pane. |
| A callback reaches nothing | Something addressed a pane id. Address by name. |
| The agent finished hours ago, unread | No watch loop. Arm it (step 2), run `catchup`. |
| `agent list` shows an unnamed agent | A wrapper launched without a rename: `herdr agent rename <pane> <name>`, then register it. |
| A prompt stalls in the input box | Read the pane, clear the dialog, send Enter (`dispatch.md`). |
| `field-audit` refuses a close: queued follow-up | Dispatch it, then `field.py queue "<name>" --done`. |
