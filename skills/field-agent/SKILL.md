---
name: field-agent
description: Use when the user asks to launch, spawn, dispatch or hand off work to another agent (claude / opus / glm / ds / opencode / pi) in a herdr tab or worktree. You act as the handler. The new agent is a field agent. This skill names the field agent, gives it a two-way reporting contract, records it in the field ledger, and arms a watch loop so you never lose track of it. Requires herdr >= 0.9.0 and HERDR_ENV=1.
---

# field-agent: dispatch a field agent and keep it

Before you use this skill, check that `HERDR_ENV=1`. If it is not `1`, tell the
user that you do not run inside a herdr pane. Then stop.

Run `herdr --version`. This skill needs **0.9.0 or later**. On an earlier
version, tell the user to run `herdr update`. Then stop.

Read the **`herdr`** skill for the command surface. This skill assumes it.
Verified against herdr 0.9.0 (2026-09-08). To run several field agents on one
theme and steer them together, use the **`field-handler`** skill instead.

This skill's directory holds `field.py`, the field ledger tool. The commands
below write `<skill_dir>` for this skill's own directory. Use the `Base
directory for this skill:` path shown at the top of this skill. `field.py`
stores its state in `~/.claude/field/`. That directory is runtime state. It is
not part of this skill.

## The model

You are the **handler**. Each agent you start is a **field agent**.

A handler does four things. All four are required.

1. **Dispatch** work with a brief that names both parties.
2. **Record** the field agent in the field ledger.
3. **Watch** the roster, so a finished agent reaches you without your attention.
4. **Triage** each report: read the work, judge it, then act or escalate.

A dispatch without steps 2 to 4 is the failure this skill exists to prevent.
The field agent finishes, nobody reads it, and the work is lost.

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

Call the pane id `<self_pane>` and the name `m`. If `m` is
taken by a live agent, use `m-<short-topic>` and use that name
everywhere below.

Read the pane id live. Do not trust `$HERDR_PANE_ID`; it goes stale after a
pane move.

## Step 2: Arm the watch loop

Do this once per session, before your first dispatch. Use the `Monitor` tool:

```
Monitor(
  description: "herdr field agents reaching done/idle/blocked",
  persistent: true,
  command: "FIELD_HANDLER_PANE=<self_pane> python3 <skill_dir>/field.py watch --interval 15"
)
```

The watcher prints one line for each status change. A quiet roster prints
nothing. Each line looks like this:

```
[FIELD] DONE | name=parser-fix | pane=w15:p7 | harness=claude | was=working | task=fix the overflow in SleepParser
[FIELD] BLOCKED | name=api-review | pane=w15:p9 | harness=opencode | was=working | task=…
[FIELD] GONE | name=doc-sweep | pane=w15:p4 | harness=pi | was=working | task=… | pane closed before the handler read it
```

Each event re-invokes you. Go to step 6 when one lands.

To find agents that finished before you armed the loop, run this once:

```bash
python3 <skill_dir>/field.py catchup
```

The ledger and the watch loop are GLOBAL to this machine. `catchup` prints
every unacknowledged agent, including ones another handler dispatched.
Read a foreign record; do not prompt or close it.

## Step 3: Choose the harness and build the request

Read the registry at `harnesses.json` in **this skill's own directory**, the
`Base directory for this skill:` path at the top of this skill. If the file is
missing or is not valid JSON, use this default and tell the user:

```json
{ "default": "claude", "prompt_on_missing": true, "harnesses": [
  { "name": "claude",   "label": "Claude (Anthropic)", "command": "claude",   "kind": "claude",   "auto_flag": "--permission-mode auto" },
  { "name": "glm",      "label": "GLM (Z.ai)",         "command": "glm",      "kind": "claude",   "auto_flag": "--permission-mode auto" },
  { "name": "ds",       "label": "DeepSeek",           "command": "ds",       "kind": "claude",   "auto_flag": "--permission-mode auto" },
  { "name": "opencode", "label": "OpenCode",           "command": "opencode", "kind": "opencode", "auto_flag": "--auto" },
  { "name": "pi",       "label": "Pi",                 "command": "pi",       "kind": "pi",       "auto_flag": "--approve" }
] }
```

`kind` is the herdr agent kind of the TUI that the command finally runs. An
entry whose `command` equals its `kind` is **canonical**; start it with
`herdr agent start`. An entry whose `command` differs (glm, ds, wrappers
around claude) is a **wrapper**; it takes the fallback path in step 5.

Flag meanings differ per harness. `--permission-mode auto` (claude family) and
`opencode --auto` auto-approve tool permissions. pi has no permission prompts;
its `--approve` skips the project-trust prompt that would block readiness.

**Sonnet is the model floor for a field agent.** Measured 2026-09-08:
`--permission-mode auto` is SILENTLY IGNORED on Haiku 4.5, so the agent stops
at its first tool call and reports `blocked` for no visible reason. Do not drop
below the floor even for a task that looks trivial. If the user asks for Haiku,
tell them this and let them decide.

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

**Choose a plain tab or a git worktree.** Use a worktree when `<request>`
implies branch work: it creates a branch, it commits a feature, it says "on its
own branch", or it edits a repo that you also edit. A field agent in your
directory that runs `git checkout -b` moves **your** branch. Otherwise use a
plain tab. When in doubt, use a plain tab and say so.

**Plain tab, in YOUR CURRENT workspace.** Never create a workspace for a field
agent, and never take the focused workspace from `herdr workspace list`; that
can belong to another client. Read your own workspace live, then put the agent
in a new tab beside you, so the user switches one tab to watch it:

```bash
WS=$(herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["workspace_id"])')
herdr tab create --workspace "$WS" --label "<name>" --cwd "<cwd>" --no-focus
```

Do NOT pass `--env HERDR_AGENT=<kind>`. Older versions of this skill did.
herdr 0.9.0 does not read that variable; it detects a wrapper harness by
sniffing the TUI it draws, so the flag was always a no-op.

**Worktree.** Run this from the repo the task concerns, or pass `--cwd`:

```bash
herdr worktree create --branch "<type>/<kebab-topic>" --label "<name>" --base <ref> --no-focus
```

Read `.result.root_pane.pane_id` from either response. Call it `<pane_id>`.
`.result.tab` and `.result.workspace` are OBJECTS, not ids; the ids are
`.result.tab.tab_id` and `.result.workspace.workspace_id`. Read the new working
directory too: `.result.worktree.path` for a worktree. If it
differs from the directory the task concerns, put **absolute paths** in the
brief.

## Step 5: Launch the harness

**Canonical harness** (`command` equals `kind`): one command starts it, names
it, and waits for readiness:

```bash
herdr agent start "<name>" --kind <kind> --pane "<pane_id>" -- <auto_flag words>
```

On a name conflict, retry once with a numeric suffix.

`agent start` needs a pane that sits at an interactive shell prompt with no
foreground command. It never creates, splits or moves layout; step 4 made the
pane. Startup defaults to a 30-second timeout. If a dialog blocks the agent
during startup, herdr returns `agent_not_ready` but keeps the name usable for
`agent read` and `agent send-keys`. Clear the dialog, then continue.

**Wrapper harness** (`command` differs from `kind`, such as glm and ds): run
it, **wait for herdr to DETECT it**, then wait for readiness, then **name it**.
Do not skip the rename; an unnamed agent breaks Rule 1:

```bash
herdr pane run "<pane_id>" "<command> <auto_flag>"

# Poll until herdr detects an agent in the pane. Measured: about 2 seconds.
for i in $(seq 1 60); do
  A=$(herdr pane get "<pane_id>" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"].get("agent") or "")')
  [ -n "$A" ] && break
  sleep 1
done
[ -z "$A" ] && echo "herdr never detected an agent in <pane_id>" && exit 1

herdr agent wait "<pane_id>" --until idle --timeout 60000
herdr agent rename "<pane_id>" "<name>"
```

CAUTION: do not drop the polling loop. `pane run` returns as soon as it sends
the command, before the TUI draws. An `agent wait` issued at that moment fails
with `agent_not_found` in about 0.04 seconds and exit 1; the `--timeout` never
applies. The `agent rename` on the next line then fails the same way, and the
agent is left running and unnamed. Measured on herdr 0.9.0.

**Clear the startup dialogs before you prompt.** Read the pane first:
`herdr pane read "<pane_id>" --source visible --lines 30`.

CAUTION: never send a blind `Enter`. Read the dialog, find the line marked
`❯`, and choose the option that matches your intent. The marked option is the
DEFAULT, and on several dialogs the default is the one you do NOT want. Move
with `Down` or `Up`, then send `Enter`.

- **Folder-trust dialog** ("Is this a project you created or one you trust?").
  The default is **"No, exit"**. "Yes, I trust this folder" is the SECOND
  option. A blind `Enter` QUITS the agent. Send `Down`, then `Enter`. This
  dialog is NOT reliable to predict: on 2026-09-08 a fresh `worktree create`
  checkout did not raise it at all. Read the pane and react to what is there;
  do not assume it appears, and do not assume it does not. `agent start` reports `interactive_ready` while this
  dialog is up, so readiness does not mean the dialog is gone.
- **Usage-credit dialog** ("Fable 5 now uses usage credits"). The default is
  **"Switch to Sonnet 5 and continue"**. A blind `Enter` silently downgrades
  the model. To keep the model you asked for, send `Down`, then `Enter`.
- **"New MCP servers found"**: send `Esc`.

Read the pane again after each keypress. Option order and defaults change
between Claude Code versions, so verify what is marked instead of trusting the
key sequence above.

CAUTION: `Enter` also submits whatever text sits in the input box. A callback
that arrived while a dialog was up is submitted as that agent's next turn.
After you clear a dialog, read the pane, and check what the agent is now
working on.

**Check the permission mode after launch. Do not assume the flag took.**
Measured on 2026-09-08: `--permission-mode auto` is silently ignored on
**Haiku 4.5**. The same flag engages on Sonnet 5 and on the glm wrapper. The
status line is the evidence:

```bash
herdr pane read "<pane_id>" --source visible --lines 3
```

`⏵⏵ auto mode on` means the flag took. `⏸ manual mode on` means it did not,
and the agent will stop at its first tool call. The handler then sees
`blocked` with no obvious cause. Use Sonnet or better for a field agent, or
expect to answer its permission prompts by hand.

If the launch fails, read the pane. A shell error (`command not found`, a stack
trace) means the launch failed; tell the user and stop. A TUI that herdr did
not detect is safe; wait about 5 seconds and continue.

## Step 6: Register the field agent in the ledger

Do this **before** you prompt. A crash between the prompt and the register call
leaves an untracked agent.

```bash
python3 <skill_dir>/field.py register "<name>" "<pane_id>" "<harness>" \
  "<one-line task summary>" --branch "<branch or omit>" --cwd "<cwd>"
```

The ledger is `~/.claude/field/ledger.json`. It survives your context
compaction and your restart. When you lose track of your agents, read it:

```bash
python3 <skill_dir>/field.py status
```

## Step 7: Send the brief

Send the request and the identity block together, as one prompt. Keep it on one
line. Use ` || ` as a separator instead of a blank line. Single-quote the inner
commands, so nothing needs escaping.

```bash
herdr agent prompt "<name>" "Field agent brief from your handler.  ||  <request>  ||  === FIELD AGENT BRIEF ===  ||  You are field agent '<name>' in herdr pane <pane_id>. Your handler is agent 'm' in pane <self_pane>.  ||  REPORT TO YOUR HANDLER by running this command, this is the only way your work reaches anyone:  herdr agent prompt 'm' 'FIELD REPORT <name>: <your message>'  ||  Report at these four moments, not only at the end: (1) START, one line when you understand the task and begin; (2) MILESTONE, one line each time you finish a meaningful unit, or roughly every 15 minutes of work; (3) BLOCKED, immediately if you need a decision, a credential, or an answer, and state the exact question; (4) COMPLETE, when you finish, with the verdict, every file path you changed, the branch name, and the test or build result.  ||  Prefix the final one with 'FIELD REPORT <name>: COMPLETE:'. Then run  herdr notification show 'Field agent done: <name>' --sound done  ||  If your report command fails, retry it twice before you continue.  ||  Do not ask the human directly. Route every question through your handler." --wait --until working --timeout 15000
```

The brief opens with the sentence `Field agent brief from your handler.` BEFORE the task. Measured 2026-09-10 on Sonnet 5: with the task first and the identity block appended after ` || `, 5 of 5 field agents read the block as a prompt injection, did the task, and sent no report (two stalled on a question aimed at a human who was not there). With the opener first, 5 of 5 reported normally. Keep the opener; the rest of the template is unchanged.

Replace `m` with your actual name from step 1.

**How to read the result.** On herdr 0.9.0, `--wait --until working` returns as
soon as the agent is working, and it returns immediately when the agent is
already working. Measured: about 0.5 seconds in both cases.

| Outcome | Meaning | What you do |
|---------|---------|-------------|
| Exit 0, `agent_status` is `working` | The turn started. | Report the dispatch. |
| Exit 0, `agent_status` is `done` or `idle` | A short turn finished already. | Read the pane. |
| `agent_blocked` | A dialog was up. herdr sent NOTHING. | Clear the dialog, then prompt again. |
| `agent_prompt_stalled` | herdr saw no activity after it submitted. | Read the pane. |

On a stall, read the pane. A prompt sent to a busy claude-kind agent QUEUES; it
does not inject into the running turn, and it is not stuck. A prompt that truly
stalled sits in the INPUT BOX with no turn started. Only then send
`herdr agent send-keys "<name>" Enter`. Retry a maximum of 3 times. If it never
submits, tell the user. Do not assume that it ran.

## Step 8: Report the dispatch to the user

State the field agent's name, its pane, its harness, its workspace and branch
for a worktree, and the checkout path. Confirm that the watch loop is armed.

For a worktree, tell the user that `herdr worktree remove --workspace <wN>`
cleans it up after a merge, and that it must run BEFORE the agent's pane
closes. That command takes only a workspace id, and a worktree workspace
disappears with its last pane; after that only `git worktree remove <path>`
can clear the checkout. The branch stays in the source repo either way.

---

## Triage: what you do when an event lands

A `[FIELD]` event or a `FIELD REPORT` message re-invokes you. Do not just
acknowledge it. Work the sequence below.

### 1. Read the work

```bash
herdr agent read "<name>" --source recent --lines 80
```

For a `COMPLETE` report, verify it. Do not trust the summary alone. Check the
files it names. Run the build or the tests when the task touched code.

### 2. Act by event type

| Event | What you do |
|-------|-------------|
| `COMPLETE` / `[FIELD] DONE` | Read and verify the work. Summarise the verdict. Send the user a `PushNotification`. Then acknowledge it. |
| `[FIELD] BLOCKED` | Read the pane. Answer it yourself when the brief makes the answer unambiguous, with `herdr agent prompt "<name>" "<answer>"`. Escalate to the user only when the decision is genuinely theirs. |
| `[FIELD] IDLE` | The agent stopped without a report. Read the pane. It has finished quietly, or it has stalled. Prompt it again, or triage it as complete. |
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

- **Do not use `herdr agent wait` to supervise.** It blocks your turn. You can
  do nothing else until it returns. The watch loop exists so that you stay
  free. `agent wait` is correct only for a short, known wait during a launch.
- **Never poll in a loop.** The watch loop notifies you. Asking an agent "are
  you done?" wastes its turn and yours.
- **Re-read ids before you use them.** A pane id you read ten minutes ago can
  point at a different pane now. Names do not have this problem.
- **When you lose track, read the ledger.** After a compaction, run
  `python3 <skill_dir>/field.py status` before you ask the user anything.
- **The ledger is the memory, not your context.** Write the task, the branch
  and the verdict into it. Your context will be summarised; the file will not.
- **Tidy up with the `field-audit` skill.** It reads each result,
  verifies it, and closes only the panes that are provably finished. Never
  close a pane with `herdr pane close` on your own judgment; an unread pane
  holds work that nothing else records.

## Failure modes and their fix

| Symptom | Cause | Fix |
|---------|-------|-----|
| A callback never arrives | The field agent crashed before its final step | The watch loop reports `GONE` or `IDLE`. Read the pane. |
| A callback reaches the wrong pane | The brief carried a pane id, and the pane moved | Address the handler by name. Rule 1. |
| The field agent asks a question that nobody sees | The brief did not tell it how to report | Every brief carries the identity block. Rule 2. |
| The agent finished hours ago, unread | No watch loop was armed | Arm it in step 2. Run `catchup` once. |
| `agent list` shows an unnamed agent | A wrapper harness was launched without a rename | `herdr agent rename <pane> <name>`, then register it. |
| A prompt stalls in the input box | Bracketed paste, or a startup dialog | Read the pane. Clear the dialog. Send Enter. |

The user's request is the message they sent with this invocation, minus any
harness-selection token consumed in step 3.
