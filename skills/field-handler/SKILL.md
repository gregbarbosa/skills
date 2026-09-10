---
name: field-handler
description: Run a room of parallel field agents on one theme and steer them from this session. Use when work splits into independent strands that could progress in parallel, such as several projects moving toward one goal. Surfaces the option and agrees scope with the user before spawning anything. Requires herdr 0.9.0 or later inside a herdr pane.
---

# field-handler: run a room of field agents

Before you use this skill, check that `HERDR_ENV=1`. If it is not `1`, tell the
user that you do not run inside a herdr pane. Then stop.

Run `herdr --version`. This skill needs **0.9.0 or later**. On an earlier
version, tell the user to run `herdr update`. Then stop.

Run `herdr --skill` for the command surface, then read the **`herdr`** skill for
the semantics it leaves out and the **`field-agent`** skill for the dispatch
contract; this is its multi-agent form, on the same ledger, watch loop and
three rules.

Two directories matter below:

- `<skill_dir>`: this skill's own directory (the `Base directory for this
  skill:` path above). It holds `handler.json`.
- `<agent_dir>`: the `field-agent` skill's directory, holding `field.py` and
  `harnesses.json`. Find it with
  `find ~/.claude ~/.agents -maxdepth 5 -type d -path '*skills/field-agent' 2>/dev/null`
  (use `find`, not an `ls` glob: zsh aborts the whole command on one unmatched
  glob). Both roots matter: single-agent installs use `~/.claude/skills`,
  multi-agent installs and Codex, Copilot, Gemini and pi use `~/.agents/skills`.

`field-agent`, `field-handler`, `field-audit` and `herdr` are one suite. If the
`find` returns nothing, the suite is not fully installed; tell the user to run
the command below, then stop.

```bash
npx skills add gregbarbosa/skills -s '*' -g -y
```

## You are the handler

**This session is the handler.** Each agent you start is a **field agent**. You
open the room, steer it, and report to the user; the watching stays here.

A handler does five things. All five are required.

1. **Agree** the scope with the user before you spawn anything.
2. **Dispatch** each field agent with a brief that names both parties.
3. **Record** every field agent in the ledger.
4. **Watch** the room, so a finished agent reaches you without your attention.
5. **Triage** each report: read the work, verify it, then act or escalate.

A field agent reports by prompting you, so its callbacks arrive as turns in
this session beside the user's own messages. Tell the user that in step 7.

## The three rules

1. **Address every agent by name, never by a pane id.** A pane id changes when
   the pane moves, and a closed pane's id resolves to nothing. A callback sent
   to a stale pane id goes nowhere.
2. **Every brief carries the identity block.** A field agent cannot report if
   it does not know your name and the exact command that reaches you.
3. **The callback is best effort. The watch loop is the guarantee.** A field
   agent that crashes sends no callback.

## Two phases

- **Phase A, offer and agree.** Name the independent strands, propose a scope,
  and discuss. Spawn nothing.
- **Phase B, open the room.** Starts only on the user's explicit go.

If this skill surfaced on its own, you are in Phase A.

## Phase A: offer and agree

1. **Offer.** In one or two sentences, name the independent strands you see.
   Offer to run them in parallel panes that you steer. Example: "This splits
   into three independent pieces. I can run a pane per piece and work them from
   here. Do you want that?"
2. **Propose a roster.** Map the goal to concrete projects. Use these sources
   in order:
   - The ledger: `python3 <agent_dir>/field.py status`. This shows work already
     dispatched, with its pane, branch and verdict.
   - Live panes: `herdr agent list` and `herdr workspace list`. The
     `terminal_title_stripped` of each agent says what it does now.
   - Dated `tries/` subdirectories and branches whose names match the goal.
   - The agent brain, for project relationships.

   Present the roster as a short list: each project, its path and branch, and
   the one job that field agent owns.
3. **Discuss.** Add or drop projects. Adjust each job. Spawn nothing yet.
4. **Get an explicit go.** Then start Phase B.

## Phase B: open the room

### Step 0: claim your own name and arm the watch loop

```bash
herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])'
herdr agent list | python3 -c 'import sys,json;print([a.get("name") for a in json.load(sys.stdin)["result"]["agents"]])'
herdr agent rename "<self_pane>" m
```

Call the pane id `<self_pane>` and the name `m`; if a live agent already holds
`m`, use `m-<short-theme>` everywhere below. Read the pane id live
(`$HERDR_PANE_ID` goes stale after a pane move), and read names with
`.get("name")`: an unnamed agent record has no `name` key.

**Arm the watch loop now, before you spawn anything.** Use the `Monitor` tool:

```
Monitor(
  description: "herdr field agents reaching done/idle/blocked",
  persistent: true,
  command: "FIELD_HANDLER_PANE=<self_pane> python3 <agent_dir>/field.py watch --interval 15"
)
```

One watch loop per machine: two share one state file and print every event
twice. If `field-agent` already armed one in this session, keep it.

Then run `python3 <agent_dir>/field.py catchup` once, to surface an agent that
settled before you armed the loop.

### Step 1: finalize the roster

Build a list of `{ project_name, agent_name, abs_path, branch, task }`, plus
the shared `theme` (one line). `agent_name` is a short kebab slug of the
project. herdr requires `[a-z][a-z0-9_-]{0,31}`; keep it under 24 characters.
Names must be unique among live agents; check `herdr agent list`. On a name
conflict at launch, retry once with a numeric suffix.

### Step 2: read the config

Read `handler.json` in `<skill_dir>`. Fields: `agent.command`,
`agent.model_flag`, `model_floor`, `layout_threshold`. If the file is missing
or is not valid JSON, use this default and tell the user:

```json
{ "agent": {"command":"claude","model_flag":"--model sonnet"}, "model_floor": "sonnet", "layout_threshold": 4 }
```

`layout_threshold` is how many field agents still share one tab: at or below
it the user sees the whole room at a glance, above it a grid makes every pane
unreadable, so each agent gets its own tab.

**`model_floor` is Sonnet.** Haiku 4.5 ignores `--permission-mode auto`, so a
Haiku field agent stops at its first tool call and shows `blocked` with no
visible cause. If the user asks for Haiku, say this and let them decide.

For a per-agent harness override that the user named, resolve `command`, `kind`
and `auto_flag` from `harnesses.json` in `<agent_dir>`. An entry whose
`command` equals its `kind` is **canonical**. An entry whose `command` differs
(glm, ds) is a **wrapper** and takes the fallback path in step 5. Read
`brief_format` from the same entry (`blocks` or `line`; missing means `blocks`)
for step 6.

### Step 3: decide isolation per field agent

A field agent needs a git worktree when BOTH of these are true:

1. Another roster entry shares its repo, or its `branch` differs from what that
   checkout has now.
2. It will commit, or change branch.

A shared-checkout agent that runs `git checkout -b` switches every session in
that directory, including this one. Two read-only agents in one repo need no
worktree; say in each task that the agent leaves git alone.

### Step 4: create the room, in the CURRENT workspace

The room lives in the workspace the user is already in: you stay in your tab,
the field agents get one tab beside it, and the user switches one tab to see
the room and back to talk to you. Read your workspace live
(`$HERDR_WORKSPACE_ID` goes stale):

```bash
WS=$(herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["workspace_id"])')
```

**N <= `layout_threshold`: ONE tab, one pane per agent.** Create the tab with
the first agent's directory, because its root pane becomes that agent's pane:

```bash
herdr tab create --workspace "$WS" --label "field agents" --cwd "<abs_path_1>" --no-focus
```

Parse `.result.tab.tab_id` and `.result.root_pane.pane_id`. That root pane is
agent 1. Then split for the rest, splitting a wide pane RIGHT and a tall one
DOWN, so the grid stays readable:

| Agent | Split |
|-------|-------|
| 2 | `herdr pane split "<pane_1>" --direction right --cwd "<abs_path_2>" --no-focus` |
| 3 | `herdr pane split "<pane_1>" --direction down --cwd "<abs_path_3>" --no-focus` |
| 4 | `herdr pane split "<pane_2>" --direction down --cwd "<abs_path_4>" --no-focus` |

Parse `.result.pane.pane_id` from each. Four agents give a 2x2 grid; three
give a split left column beside a full-height right column.

**N > `layout_threshold`: one tab per agent, still in `$WS`.** Above four,
a grid gives each agent an unusably narrow column, so trade the single glance
for readable panes:

```bash
herdr tab create --workspace "$WS" --label "<project>" --cwd "<abs_path>" --no-focus
```

Parse `.result.root_pane.pane_id`.

**Worktree agents are the one exception.** `worktree create` always makes its
own workspace, so those agents live outside the user's. Say so in step 7.

```bash
herdr worktree create --cwd "<repo>" --branch "<branch>" --label "<project>" --no-focus
```

Parse `.result.root_pane.pane_id` and note `.result.worktree.path`; put
absolute paths in that agent's task, since its checkout is not the repo the
user is looking at. A worktree workspace closes with its last pane and
`herdr worktree remove` takes only `--workspace ID`, so remove the worktree
before its pane closes (`field-audit` does this in order); afterwards only
`git worktree remove` clears the checkout.

### Step 5: launch and register every field agent

Launch and register every field agent before you prompt any of them.

**Canonical harness:**

```bash
herdr agent start "<agent_name>" --kind <kind> --pane "<pane_id>" -- <model_flag words> <auto_flag words>
```

`agent start` needs a pane sitting at a shell prompt (step 4 made it) and
times out after 30 seconds. A startup dialog returns `agent_not_ready` with
the name still usable for `agent read` and `agent send-keys`: clear the
dialog, then continue.

**Wrapper harness** (glm, ds): run it, wait for herdr to detect it, wait for
readiness, then name it (Rule 1):

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
herdr agent rename "<pane_id>" "<agent_name>"
```

**Clear the startup dialogs before you prompt.** Read the pane
(`herdr pane read "<pane_id>" --source visible --lines 30`), find the line
marked `❯`, and move to the option you want with `Down` or `Up` before
`Enter`: the marked option is the default, and on these dialogs the default is
the wrong one. Read the pane again after each keypress; option order changes
between Claude Code versions.

- **Folder trust** ("Is this a project you created or one you trust?"): the
  default is "No, exit", which quits the agent. `Down`, then `Enter`. It does
  not always appear.
- **Usage credits** ("Fable 5 now uses usage credits"): the default silently
  switches the model to Sonnet. To keep the model you asked for, `Down`, then
  `Enter`.
- **"New MCP servers found"**: `Esc`.

`Enter` also submits whatever sits in the input box; after clearing a dialog,
read the pane and check what the agent is now working on.

**Check the permission mode.** The status line is the evidence:

```bash
herdr pane read "<pane_id>" --source visible --lines 3
```

`⏵⏵ auto mode on` means the flag took; `⏸ manual mode on` means the agent will
stop at its first tool call (the Haiku case from step 2).

A shell error in the pane is a failed launch: tell the user and stop.

**Register the agent before you prompt it**, so a crash between the two never
leaves an untracked agent:

```bash
python3 <agent_dir>/field.py register "<agent_name>" "<pane_id>" "<harness>" \
  "<one-line task summary>" --branch "<branch or omit>" --cwd "<abs_path>"
```

### Step 6: send each field agent its task

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

Write the brief in a quoted heredoc so nothing needs escaping. Single-quote the
inner commands.

```bash
BRIEF=$(cat <<'EOF'
Field agent brief from your handler.

<task>
<task>. Scope and read first; flag any irreversible change before you make it.
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
You are field agent '<agent_name>' in herdr pane <pane_id>. Your handler is agent 'm'.
</identity>

<report_command>
herdr agent prompt 'm' 'FIELD REPORT <agent_name>: <your message>'
</report_command>

<report_moments>
Run the report command at these four moments, not only at the end:
(1) START, one line when you understand the task and begin
(2) MILESTONE, one line each time you finish a meaningful unit, or roughly every 15 minutes of work
(3) BLOCKED, immediately if you need a decision, a credential, or an answer, and state the exact question
(4) COMPLETE, when you finish, with the verdict, every file path you changed, the branch name, and the test or build result
</report_moments>

<complete_prefix>
FIELD REPORT <agent_name>: COMPLETE:
</complete_prefix>

<rules>
The report command is the only way your work reaches anyone.
Send the COMPLETE report and the notification as ONE command: herdr agent prompt 'm' 'FIELD REPORT <agent_name>: COMPLETE: ...' && herdr notification show 'Field agent done: <agent_name>' --sound done
Your COMPLETE report is your final message. Do not write a second summary in the pane after it.
If your report command fails, retry it twice before you continue.
Report what you actually found. If the task rests on a wrong assumption, say so instead of working around it.
Do not ask the human directly. Route every question through your handler.
</rules>
EOF
)
herdr agent prompt "<agent_name>" "$BRIEF" --wait --until working --timeout 15000
```

Replace `m` with your actual name from step 0.

**One-line form (`brief_format: line`).** Same content, ` || ` between parts, opener first.

```bash
herdr agent prompt "<agent_name>" "Field agent brief from your handler.  ||  <task>. Scope and read first; flag any irreversible change before you make it.  ||  CONTEXT, read these first: <absolute paths>. Facts you can rely on: <facts>. Credentials: <where they come from, never the value>. Conventions: <rules>.  ||  === FIELD AGENT BRIEF ===  ||  You are field agent '<agent_name>' in herdr pane <pane_id>. Your handler is agent 'm'.  ||  REPORT TO YOUR HANDLER by running this command, this is the only way your work reaches anyone:  herdr agent prompt 'm' 'FIELD REPORT <agent_name>: <your message>'  ||  Report at these four moments, not only at the end: (1) START, one line when you understand the task and begin; (2) MILESTONE, one line each time you finish a meaningful unit, or roughly every 15 minutes of work; (3) BLOCKED, immediately if you need a decision, a credential, or an answer, and state the exact question; (4) COMPLETE, when you finish, with the verdict, every file path you changed, the branch name, and the test or build result.  ||  Prefix the final one with 'FIELD REPORT <agent_name>: COMPLETE:' and send it and the notification as ONE command: herdr agent prompt 'm' 'FIELD REPORT <agent_name>: COMPLETE: ...' && herdr notification show 'Field agent done: <agent_name>' --sound done  ||  Your COMPLETE report is your final message; do not write a second summary after it.  ||  If your report command fails, retry it twice before you continue.  ||  Report what you actually found. If the task rests on a wrong assumption, say so instead of working around it.  ||  Do not ask the human directly. Route every question through your handler." --wait --until working --timeout 15000
```

**How to read the result.** `--wait --until working` returns as soon as the
agent is working, at once if it already was.

| Outcome | Meaning | What you do |
|---------|---------|-------------|
| Exit 0, `agent_status` is `working` | The turn started. | Go to the next agent. |
| Exit 0, `agent_status` is `done` or `idle` | A short turn finished already. | Read the pane. |
| `agent_blocked` | A dialog was up. herdr sent NOTHING. | Clear the dialog, then prompt again. |
| `agent_prompt_stalled` | herdr saw no activity after it submitted. | Read the pane. |

On a stall, read the pane. A prompt sent to a busy claude-kind agent queues
for its next turn and is not stuck. Input-box text is stuck only when it matches
what you just sent; then send `herdr agent send-keys "<agent_name>" Enter`, at
most 3 times. If it never submits, tell the user rather than assuming it ran.

### Step 7: announce, then work the room

State in one line which field agents are up, their models, the TAB that holds
them, which agents hold their own worktree (those sit in their own workspace,
not the user's), and that the watch loop is armed.

Then tell the user that this session now works the room, so their own
conversation here will share turns with the agents' reports. Offer `/loop` if
they want it to run hands-off.

Example: "Room up in tab 'field agents' beside this one: 3 Sonnet field agents
(a, b, c); c holds its own worktree, so it sits in its own workspace. Watch
loop armed. I will work the room from here, so this thread will fill with
their reports; switch to that tab to watch them, or leave it to me."

---

## Your standing duties while the room runs

**Run one assessment pass now.** `herdr agent list` gives every agent's
`agent_status` and live `terminal_title_stripped`; cross-check it against the
roster. A roster agent missing from the list is not gone (detection lags on a
fresh worktree pane): `herdr pane read` its pane directly. Read only the agents
that look stuck, off-theme or missing, with
`herdr agent read <agent_name> --source recent-unwrapped --lines 40`, and give
the user a short roll-up.

**Address agents by name:** `herdr agent prompt <agent_name> "<one concrete
instruction>"`. Prompt an agent whose status is `idle`, `blocked` or `done`; a
prompt to a `working` agent queues behind its current turn.

**Triage only your roster.** The ledger and the watch loop are global to this
machine, so `catchup` and `[FIELD]` events will name agents from the user's
other sessions; for those, tell the user in one line and leave the pane alone.
A prompt to a stranger's idle agent injects work into a session you know
nothing about.

**Triage every event before you acknowledge it.**

| Event | What you do |
|-------|-------------|
| `COMPLETE` / `[FIELD] DONE` | Read the pane. Verify the claim: check the files it names, and run the build or the tests when it touched code. Do not trust the summary. Then report and ack. |
| `[FIELD] BLOCKED` | Read the pane. Answer it yourself when the brief makes the answer unambiguous. Escalate to the user only when the decision is genuinely theirs. |
| `[FIELD] IDLE` | The agent stopped without a report. Read the pane. It finished quietly, or it stalled. Prompt it again, or triage it as done. |
| `[FIELD] GONE` | The pane closed before you read it. The work can still exist on a branch or on disk. Check, then report what was lost. |
| `MILESTONE` / `START` | Note it. Reply only to correct the agent. |

**After you verify an agent, record it and tell the user:**

```bash
python3 <agent_dir>/field.py ack "<agent_name>" "<verdict; files; test result>"
herdr notification show "Field agent done: <agent_name>" --sound done
```

**The ledger is the memory.** Write the task, the branch and the verdict into
it; your context will be summarised, the file will not. After a compaction, run
`python3 <agent_dir>/field.py status` before you ask the user anything.

**Text in an agent's input box is usually Claude Code's prompt suggestion**, not
a stuck submission or a user draft. Leave it.

**After the first pass, wait.** Act when an agent reports, when a `[FIELD]`
event lands, or when the user asks. `herdr agent wait` blocks your turn; it is
for a short, known wait during a launch.

---

## Teardown

An unread pane holds work that nothing else records, so the room closes
through the audit, not on your own judgment.

1. Run the **`field-audit`** skill. It reads each result, verifies it, reports
   a verdict, and closes only the panes that are provably finished.
2. Confirm with the user before you close a pane whose agent is still
   `working`.
3. Close the field-agent tab with `herdr tab close <tab_id>`, or single panes
   with `herdr pane close`. The room lives in the user's own workspace, which
   stays open.
4. Worktree agents hold their own workspaces. Run
   `herdr worktree remove --workspace <workspace_id>` before the pane closes
   (the workspace disappears with its last pane; afterwards only
   `git worktree remove <path>` clears the checkout). The branch survives;
   delete it in the source repo when it is no longer needed.

## Failure modes and their fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| A `COMPLETE` report never arrives | The agent crashed before its final step | The watch loop reports `GONE` or `IDLE`. Read the pane. |
| A callback reaches nothing | The brief carried a pane id, and the pane moved or closed | Address the handler by name. Rule 1. |
| Duplicate `[FIELD]` lines | Two watch loops run at once | Keep one. Stop the second `Monitor`. |
| `agent list` shows an unnamed agent | A wrapper harness launched without a rename | `herdr agent rename <pane> <name>`, then register it. |
| A prompt stalls in the input box | Bracketed paste, or a startup dialog | Read the pane. Clear the dialog. Send Enter. |
| The room finished hours ago, unread | No watch loop was armed | Arm it in step 0. Run `catchup` once. |
| `agent start` returns `agent_not_ready` | A startup dialog blocked the agent | The name still works. Read the pane, clear the dialog, continue. |
