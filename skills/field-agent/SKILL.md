---
name: field-agent
description: Dispatch one field agent (claude, glm, ds, opencode or pi) into a herdr tab or worktree with a reporting contract, a ledger record and a watch loop. Use when the user asks to launch, spawn, dispatch or hand off work to another agent. Several agents on one theme is field-handler. Requires herdr 0.9.0 or later inside a herdr pane.
---

# field-agent: dispatch a field agent and keep it

Before you use this skill, check that `HERDR_ENV=1`. If it is not `1`, tell the
user that you do not run inside a herdr pane. Then stop.

Run `herdr --version`. This skill needs **0.9.0 or later**. On an earlier
version, tell the user to run `herdr update`. Then stop.

Run `herdr --skill` for the command surface, then read the **`herdr`** skill for
the semantics it leaves out. Several field agents on one theme is the
**`field-handler`** skill.

`<skill_dir>` below is this skill's own directory (the `Base directory for this
skill:` path above). It holds `field.py`, the ledger tool, whose state lives in
`~/.claude/field/`.

## The model

You are the **handler**. Each agent you start is a **field agent**.

A handler does four things. All four are required.

1. **Dispatch** work with a brief that names both parties.
2. **Record** the field agent in the field ledger.
3. **Watch** the roster, so a finished agent reaches you without your attention.
4. **Triage** each report: read the work, judge it, then act or escalate.

Skip 2 to 4 and the field agent finishes, nobody reads it, and the work is lost.

## The three rules

**Rule 1: Name everything. Address by name, never by pane id.**
A pane id changes when the pane moves, and a closed pane's id resolves to
nothing. A callback sent to a stale pane id goes nowhere. Every field agent
gets a name. You get a name. Every message between you uses names.

**Rule 2: Every brief carries the identity block.**
A field agent cannot report to you if it does not know who you are. The brief
always states the field agent's own name and pane, your name and pane, and the
exact command that reaches you.

**Rule 3: The callback is best effort. The watch loop is the guarantee.**
A field agent that crashes sends no callback. Arm the watch loop, so herdr's
own status detection catches what the callback misses.

---

## Step 1: Claim your own handler name

Do this once per session, before your first dispatch.

```bash
SELF=$(herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr agent rename "$SELF" m
echo "$SELF"
```

Call the pane id `<self_pane>` and the name `m`. If `m` is taken by a live
agent, use `m-<short-topic>` everywhere below. Read the pane id live;
`$HERDR_PANE_ID` goes stale after a pane move.

## Step 2: Arm the watch loop

Do this once per session, before your first dispatch. Use the `Monitor` tool:

```
Monitor(
  description: "herdr field agents reaching done/idle/blocked",
  persistent: true,
  command: "FIELD_HANDLER_PANE=<self_pane> python3 <skill_dir>/field.py watch --interval 15"
)
```

The watcher prints one line per status change and re-invokes you; a quiet
roster prints nothing. Go to Triage when a line lands:

```
[FIELD] DONE | name=parser-fix | pane=w15:p7 | harness=claude | was=working | task=fix the overflow in SleepParser
[FIELD] GONE | name=doc-sweep | pane=w15:p4 | harness=pi | was=working | task=… | pane closed before the handler read it
```

To find agents that finished before you armed the loop, run this once:

```bash
python3 <skill_dir>/field.py catchup
```

The ledger and the watch loop are global to this machine, so `catchup` also
lists agents another handler dispatched. Read a foreign record; leave it to
its handler.

## Step 3: Choose the harness and build the request

Read `<skill_dir>/harnesses.json`. If it is missing or invalid, use this
default and tell the user:

```json
{ "default": "claude", "prompt_on_missing": true, "harnesses": [
  { "name": "claude",   "label": "Claude (Anthropic)", "command": "claude",   "kind": "claude",   "auto_flag": "--permission-mode auto", "brief_format": "blocks" },
  { "name": "glm",      "label": "GLM (Z.ai)",         "command": "glm",      "kind": "claude",   "auto_flag": "--permission-mode auto", "brief_format": "blocks" },
  { "name": "ds",       "label": "DeepSeek",           "command": "ds",       "kind": "claude",   "auto_flag": "--permission-mode auto", "brief_format": "blocks" },
  { "name": "opencode", "label": "OpenCode",           "command": "opencode", "kind": "opencode", "auto_flag": "--auto", "brief_format": "line" },
  { "name": "pi",       "label": "Pi",                 "command": "pi",       "kind": "pi",       "auto_flag": "--approve", "brief_format": "line" }
] }
```

`kind` is the herdr agent kind of the TUI that the command finally runs. An
entry whose `command` equals its `kind` is **canonical**; start it with
`herdr agent start`. An entry whose `command` differs (glm, ds, wrappers
around claude) is a **wrapper**; it takes the fallback path in step 5.

`brief_format` picks the brief form in step 7: `blocks` (multi-line, tagged)
where a multi-line paste is known to arrive intact, `line` (` || ` separators)
until a harness has passed that check. Missing means `blocks`.

`--permission-mode auto` (claude family) and `opencode --auto` auto-approve
tool permissions; pi has none, and its `--approve` skips the project-trust
prompt.

**Sonnet is the model floor.** Haiku 4.5 ignores `--permission-mode auto`, so
the agent stops at its first tool call and shows `blocked` with no visible
cause. If the user asks for Haiku, say this and let them decide.

Detect the harness from the user's message. Then build `<request>`:

- **Explicit:** the message starts with `--harness <name>` or `-h <name>`.
  Select `<name>`. Remove the flag and the name.
- **Bare token:** the first word equals a registry `name`. Select it. Remove
  that word.
- **None:** keep the whole message. If `prompt_on_missing` is true, show a
  numbered menu of labels. A blank reply selects `default`. If it is false,
  use `default` and say nothing.

| User message | Harness | `<request>` |
|---|---|---|
| `opencode refactor the auth module` | opencode | `refactor the auth module` |
| `--harness glm fix the flaky test` | glm | `fix the flaky test` |
| `-h pi summarize this thread` | pi | `summarize this thread` |
| `refactor the auth module` | menu, blank = claude | `refactor the auth module` |

Call the entry's values `<command>`, `<auto_flag>` and `<kind>`.

## Step 4: Name the field agent and choose its pane

Derive `<name>`: kebab-case, a maximum of 24 characters, taken from the task.
Examples: `parser-overflow`, `api-test-coverage`, `qring-teardown`. The name
must be unique among live agents. Check with `herdr agent list`.

**Plain tab or git worktree.** A worktree when `<request>` implies branch
work (creates a branch, commits a feature, says "on its own branch", or edits a
repo you also edit: a field agent in your directory that runs `git checkout -b`
moves **your** branch). Otherwise a plain tab; when in doubt, plain tab, and
say so.

**Plain tab, in your current workspace.** Read your own workspace live (the
focused workspace in `herdr workspace list` can belong to another client) and
put the agent in a new tab beside you:

```bash
WS=$(herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["workspace_id"])')
herdr tab create --workspace "$WS" --label "<name>" --cwd "<cwd>" --no-focus
```

**Worktree.** Run this from the repo the task concerns, or pass `--cwd`:

```bash
herdr worktree create --branch "<type>/<kebab-topic>" --label "<name>" --base <ref> --no-focus
```

Read `.result.root_pane.pane_id` from either response; call it `<pane_id>`.
`.result.tab` and `.result.workspace` are objects; the ids are
`.result.tab.tab_id` and `.result.workspace.workspace_id`. For a worktree, read
`.result.worktree.path` and put absolute paths in the brief.

A worktree opens in its own workspace. To keep the agent beside you, move its
pane into a tab of yours and continue with the new id the move returns:

```bash
herdr pane move "<pane_id>" --new-tab --workspace "$WS" --label "<name>" --no-focus
```

`<pane_id>` is then `.result.move_result.pane.pane_id`; the temporary
workspace closes itself.

## Step 5: Launch the harness

**Canonical harness** (`command` equals `kind`): one command starts it, names
it, and waits for readiness:

```bash
herdr agent start "<name>" --kind <kind> --pane "<pane_id>" -- <auto_flag words>
```

On a name conflict, retry once with a numeric suffix.

`agent start` needs a pane sitting at a shell prompt (step 4 made it) and
times out after 30 seconds. A startup dialog returns `agent_not_ready` with
the name still usable for `agent read` and `agent send-keys`: clear the
dialog, then continue.

**Wrapper harness** (`command` differs from `kind`: glm, ds): run it, wait
for herdr to detect it, wait for readiness, then name it (Rule 1):

```bash
herdr pane run "<pane_id>" "<command> <auto_flag>"

# pane run returns before the TUI draws; without this loop, agent wait fails
# at once with agent_not_found and the agent is left running and unnamed.
for i in $(seq 1 60); do
  A=$(herdr pane get "<pane_id>" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"].get("agent") or "")')
  [ -n "$A" ] && break
  sleep 1
done
[ -z "$A" ] && echo "herdr never detected an agent in <pane_id>" && exit 1

herdr agent wait "<pane_id>" --until idle --timeout 60000
herdr agent rename "<pane_id>" "<name>"
```

**Clear the startup dialogs before you prompt.** Read the pane
(`herdr pane read "<pane_id>" --source visible --lines 30`), find the line
marked `❯`, and move to the option you want with `Down` or `Up` before
`Enter`: the marked option is the default, and on these dialogs the default is
the wrong one. Read the pane again after each keypress; option order changes
between Claude Code versions.

- **Folder trust** ("Is this a project you created or one you trust?"): the
  default is "No, exit", which quits the agent. `Down`, then `Enter`. It does
  not always appear, and `agent start` reports ready while it is up.
- **Usage credits** ("Fable 5 now uses usage credits"): the default silently
  switches the model to Sonnet. To keep the model you asked for, `Down`, then
  `Enter`.
- **"New MCP servers found"**: `Esc`.

`Enter` also submits whatever sits in the input box, so a callback that
arrived during a dialog becomes the agent's next turn. After clearing a
dialog, read the pane and check what the agent is now working on.

**Check the permission mode.** The status line is the evidence:

```bash
herdr pane read "<pane_id>" --source visible --lines 3
```

`⏵⏵ auto mode on` means the flag took; `⏸ manual mode on` means the agent will
stop at its first tool call (the Haiku case from step 3).

If the launch fails, read the pane. A shell error (`command not found`, a stack
trace) is a failed launch: tell the user and stop. A TUI herdr has not detected
yet is fine: wait about 5 seconds and continue.

## Step 6: Register the field agent in the ledger

Do this before you prompt, so a crash between the two never leaves an
untracked agent.

```bash
python3 <skill_dir>/field.py register "<name>" "<pane_id>" "<harness>" \
  "<one-line task summary>" --branch "<branch or omit>" --cwd "<cwd>"
```

The ledger (`~/.claude/field/ledger.json`) survives your compaction and your
restart. When you lose track of your agents, read it:

```bash
python3 <skill_dir>/field.py status
```

## Step 7: Send the brief

One prompt, two halves: the task with everything the agent needs, then the
reporting contract. herdr delivers a multi-line prompt intact (bracketed paste;
the pane shows it collapsed as `[Pasted text +N lines]`, the transcript holds it).
Read `brief_format` from the harness entry: `blocks` is the form below, `line` is
the one-line fallback further down.

Keep the opener first. It is what tells the agent the message is a brief; without
it Sonnet 5 reads the identity block as an injection and goes silent (5 of 5 runs).

Fill the context block. A field agent starts with an empty context window, so give
it what you would tell a new teammate: files to read first (absolute paths), facts
already established, where credentials come from (never the value), and the
conventions that apply. Delete any line you have nothing for.

Fill the time block when you can estimate the task. Set the budget somewhat above the time you want spent: agents pace to finish inside it and usually finish early. Without an estimate, keep only the "Time matters" sentence. The budget is advisory, so keep your own timeout for a hard stop.

Write the brief in a quoted heredoc so nothing needs escaping. Single-quote the
inner commands.

```bash
BRIEF=$(cat <<'EOF'
Field agent brief from your handler.

<task>
<request>
</task>

<context>
Read these first, in this order:
- <absolute path to the CLAUDE.md or AGENTS.md of the repo the task concerns>
- <absolute path to the README, spec, plan, or prior deliverable the task builds on>
Facts you can rely on:
- <a decision, number, or gotcha already established, one per line>
Credentials and access:
- <where a key or token comes from: a path or a command, never the value>
Conventions:
- <no em-dashes; do not git add, commit, or change branch; the rules of this repo>
</context>

<identity>
You are field agent '<name>' in herdr pane <pane_id>. Your handler is agent 'm' in pane <self_pane>.
</identity>

<report_command>
herdr agent prompt 'm' 'FIELD REPORT <name>: <your message>'
</report_command>

<report_moments>
Run the report command at these four moments, not only at the end:
(1) START, one line when you understand the task and begin
(2) MILESTONE, one line each time you finish a meaningful unit, or roughly every 15 minutes of work
(3) BLOCKED, immediately if you need a decision, a credential, or an answer, and state the exact question
(4) COMPLETE, when you finish, with the verdict, every file path you changed, the branch name, and the test or build result
</report_moments>

<complete_prefix>
FIELD REPORT <name>: COMPLETE:
</complete_prefix>

<time>
Started <HH:MM from date>. Budget about <N> minutes, advisory: check date at each milestone and pace to finish inside it. Time matters here: do not spend time that can be avoided, and the earlier a correct result is obtained, the better.
</time>

<rules>
The report command is the only way your work reaches anyone.
Send the COMPLETE report and the notification as ONE command: herdr agent prompt 'm' 'FIELD REPORT <name>: COMPLETE: ...' && herdr notification show 'Field agent done: <name>' --sound done
Your COMPLETE report is your final message. Do not write a second summary in the pane after it.
Your turn ends only with a COMPLETE or a BLOCKED report. Do not stop on a summary that announces the next step, an offer to continue unless told otherwise, a list of decisions that block nothing, or a milestone that feels like a good place to report. Send the MILESTONE report in the same message as your next tool call and keep working. Before a risky or irreversible action, report BLOCKED and wait.
Before you change anything, read the files that the task can depend on, including files that this brief does not name.
Keep the parts of your task as a checklist in ~/.claude/field/checklists/<name>.md (create it at START). Tick each item when it is done. Send COMPLETE only when every item is ticked; otherwise send BLOCKED and name the open items.
If your report command fails, retry it twice before you continue.
Report what you actually found. If the task rests on a wrong assumption, say so instead of working around it.
Do not ask the human directly. Route every question through your handler.
</rules>
EOF
)
herdr agent prompt "<name>" "$BRIEF" --wait --until working --timeout 15000
```

Replace `m` with your actual name from step 1.

**One-line form (`brief_format: line`).** Same content, ` || ` between parts, opener first.

```bash
herdr agent prompt "<name>" "Field agent brief from your handler.  ||  <request>  ||  CONTEXT, read these first: <absolute paths>. Facts you can rely on: <facts>. Credentials: <where they come from, never the value>. Conventions: <rules>.  ||  === FIELD AGENT BRIEF ===  ||  You are field agent '<name>' in herdr pane <pane_id>. Your handler is agent 'm' in pane <self_pane>.  ||  REPORT TO YOUR HANDLER by running this command, this is the only way your work reaches anyone:  herdr agent prompt 'm' 'FIELD REPORT <name>: <your message>'  ||  Report at these four moments, not only at the end: (1) START, one line when you understand the task and begin; (2) MILESTONE, one line each time you finish a meaningful unit, or roughly every 15 minutes of work; (3) BLOCKED, immediately if you need a decision, a credential, or an answer, and state the exact question; (4) COMPLETE, when you finish, with the verdict, every file path you changed, the branch name, and the test or build result.  ||  Prefix the final one with 'FIELD REPORT <name>: COMPLETE:' and send it and the notification as ONE command: herdr agent prompt 'm' 'FIELD REPORT <name>: COMPLETE: ...' && herdr notification show 'Field agent done: <name>' --sound done  ||  Your COMPLETE report is your final message; do not write a second summary after it.  ||  Your turn ends only with a COMPLETE or a BLOCKED report. Do not stop on a summary that announces the next step, an offer to continue unless told otherwise, a list of decisions that block nothing, or a milestone that feels like a good place to report. Send the MILESTONE report in the same message as your next tool call and keep working. Before a risky or irreversible action, report BLOCKED and wait.  ||  Before you change anything, read the files that the task can depend on, including files that this brief does not name.  ||  Keep the parts of your task as a checklist in ~/.claude/field/checklists/<name>.md (create it at START). Tick each item when it is done. Send COMPLETE only when every item is ticked; otherwise send BLOCKED and name the open items.  ||  Started <HH:MM>; budget about <N> minutes, advisory; time matters, so the earlier a correct result, the better.  ||  If your report command fails, retry it twice before you continue.  ||  Report what you actually found. If the task rests on a wrong assumption, say so instead of working around it.  ||  Do not ask the human directly. Route every question through your handler." --wait --until working --timeout 15000
```

**How to read the result.** `--wait --until working` returns as soon as the
agent is working, at once if it already was.

| Outcome | Meaning | What you do |
|---------|---------|-------------|
| Exit 0, `agent_status` is `working` | The turn started. | Report the dispatch. |
| Exit 0, `agent_status` is `done` or `idle` | A short turn finished already. | Read the pane. |
| `agent_blocked` | A dialog was up. herdr sent NOTHING. | Clear the dialog, then prompt again. |
| `agent_prompt_stalled` | herdr saw no activity after it submitted. | Read the pane. |

On a stall, read the pane. A prompt sent to a busy claude-kind agent queues
for its next turn and is not stuck. A stalled prompt sits in the input box with
no turn started; only then send `herdr agent send-keys "<name>" Enter`, at most
3 times. If it never submits, tell the user rather than assuming it ran.

## Step 8: Report the dispatch to the user

State the field agent's name, its pane, its harness, its workspace and branch
for a worktree, and the checkout path. Confirm that the watch loop is armed.

For a worktree left in its own workspace, tell the user that
`herdr worktree remove --workspace <wN>` cleans it up after a merge and must
run before the agent's pane closes: the workspace disappears with its last
pane. For a worktree moved beside you, and after any workspace is gone, only
`git worktree remove <path>` clears the checkout. The branch stays either way.

---

## Triage: what you do when an event lands

A `[FIELD]` event or a `FIELD REPORT` message re-invokes you. Work the
sequence below before you acknowledge.

### 1. Read the work

```bash
herdr agent read "<name>" --source recent --lines 80
```

Verify a `COMPLETE` report against the files it names, and run the build or
the tests when the task touched code.

### 2. Act by event type

| Event | What you do |
|-------|-------------|
| `COMPLETE` / `[FIELD] DONE` | Read and verify the work. Summarise the verdict. Send the user a `PushNotification`. Then acknowledge it. |
| `[FIELD] BLOCKED` | Read the pane. Answer it yourself when the brief makes the answer unambiguous, with `herdr agent prompt "<name>" "<answer>"`. Escalate to the user only when the decision is genuinely theirs. |
| `[FIELD] IDLE` | The agent stopped without a report. Read the pane. Read its checklist in `~/.claude/field/checklists/`: an unticked item is open work, whatever the last message says. If it finished quietly, triage it as complete. If work is still open and no blocker is stated, prompt it naming the open items: "Still open: <items>. Continue. If one is blocked, report BLOCKED and say what blocks it." Stop after two or three such nudges on the same task and tell the user it is stuck. |
| `[FIELD] GONE` | The pane closed before you read it. The work can still exist on disk or on a branch. Check the branch and the files, then tell the user what was lost. |
| `MILESTONE` / `START` | Note it. Reply only when the field agent needs a correction. |

### 3. Dispatch the queued follow-up

If the ledger record holds a `queued_followup`, dispatch it now, without
waiting for the user. Use a fresh field agent for a new task. Use
`herdr agent prompt "<name>" "<follow-up>"` to continue the same agent.

Queue a follow-up when you dispatch, or at any time:

```bash
python3 <skill_dir>/field.py queue "<name>" "after the parser fix lands, update PROVENANCE.md"
```

### 4. Acknowledge

Acknowledgement is what stops the same event from resurfacing:

```bash
python3 <skill_dir>/field.py ack "<name>" "verified; 3 files changed; tests pass"
```

---

## Standing duties while your agents run

- **Supervise through the watch loop.** `herdr agent wait` blocks your turn;
  it is for a short, known wait during a launch. Asking an agent whether it is
  done wastes its turn and yours.
- **Address by name.** A pane id you read ten minutes ago can point at a
  different pane now.
- **The ledger is the memory.** Write the task, the branch and the verdict into
  it; your context will be summarised, the file will not. After a compaction,
  run `python3 <skill_dir>/field.py status` before you ask the user anything.
- **Tidy up with `field-audit`.** It reads each result, verifies it, and closes
  only panes that are provably finished. An unread pane holds work nothing else
  records.

## Failure modes and their fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| A callback never arrives | The field agent crashed before its final step | The watch loop reports `GONE` or `IDLE`. Read the pane. |
| A callback reaches the wrong pane | The brief carried a pane id, and the pane moved | Address the handler by name. Rule 1. |
| The field agent asks a question that nobody sees | The brief did not tell it how to report | Every brief carries the identity block. Rule 2. |
| The agent finished hours ago, unread | No watch loop was armed | Arm it in step 2. Run `catchup` once. |
| `agent list` shows an unnamed agent | A wrapper harness was launched without a rename | `herdr agent rename <pane> <name>`, then register it. |
| A prompt stalls in the input box | Bracketed paste, or a startup dialog | Read the pane. Clear the dialog. Send Enter. |
