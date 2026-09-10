---
name: field-audit
description: Read each dispatched field agent's result, verify it, report a verdict, then close only the panes that are provably finished. Use when the user asks to audit, sweep, tidy or close the agents and panes you dispatched. Requires herdr 0.9.0 or later inside a herdr pane.
---

# field-audit: read the results, then close what is finished

Before you use this skill, check that `HERDR_ENV=1`. If it is not `1`, tell the
user that you do not run inside a herdr pane. Then stop.

Run `herdr --version`. This skill needs **0.9.0 or later**. On an earlier
version, tell the user to run `herdr update`. Then stop.

A closed pane destroys unread output, so this skill reads first and closes
last. **`field-agent`** dispatches one field agent, **`field-handler`** runs a
room, **`herdr`** carries the semantics `herdr --skill` leaves out; the four
are one suite.

The ledger tool `field.py` lives in the `field-agent` skill's directory (one
copy, so it cannot go stale). Find it once and call it `<agent_dir>`:

```bash
find ~/.claude ~/.agents -maxdepth 5 -type d -path '*skills/field-agent' 2>/dev/null
```

Use `find`, not an `ls` glob (zsh aborts the whole command on one unmatched
glob). Both roots matter: single-agent installs use `~/.claude/skills`,
multi-agent installs and Codex, Copilot, Gemini and pi use `~/.agents/skills`.
`field.py` keeps its state in `~/.claude/field/`.

If the `find` returns nothing, the suite is not fully installed; tell the user
to run the command below, then stop.

```bash
npx skills add gregbarbosa/skills -s '*' -g -y
```

## The rule

**Read a pane's result before you close it.** The output is the point of a
field agent; a close before a read throws the work away and leaves no trace.

## Step 1: Take the inventory

```bash
SELF=$(herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
FIELD_HANDLER_PANE=$SELF python3 <agent_dir>/field.py audit --include-loose
```

Each agent gets a verdict:

| Verdict | Meaning | What you do |
|---------|---------|-------------|
| `CLOSE` | Settled, acknowledged, working tree clean | Safe to close in step 4. |
| `HOLD` | A named reason blocks the close | Do not close it. Fix the cause first. |
| `ASK` | The agent is not in the ledger | The handler did not dispatch it. Step 3. |

Drop `--include-loose` to see only the agents you dispatched.

## Step 2: Read every settled agent you dispatched

For each agent that is `idle`, `done` or `blocked`:

```bash
herdr agent read "<name>" --source recent --lines 80
```

Then judge the work against the files, not the summary line:

- Check that the files it names exist and hold the change.
- Run the build or the tests when the task touched code.
- Check the branch when the task was branch work.

Record the verdict, then acknowledge it. Acknowledgement is what makes the
agent eligible to close:

```bash
python3 <agent_dir>/field.py ack "<name>" "verified: 3 files changed, tests pass"
```

Incomplete work stays unacknowledged; prompt the agent to finish:

```bash
herdr agent prompt "<name>" "<what is missing>"
```

If the agent is `blocked`, read its question. Answer it when the brief makes
the answer unambiguous. Escalate to the user when the decision is theirs.

## Step 3: Handle the `ASK` agents

An `ASK` agent is not in your ledger. You did not dispatch it, or you
dispatched it in an earlier session that is now gone.

**An `ASK` agent closes only on the user's word.** It can be their own
interactive session: a pane at the home directory, titled for the user rather
than a task, is almost certainly them working.

Read each `ASK` agent, then tell the user what it holds and ask whether to
close it, all of them in one question.

If the user confirms that an untracked agent was a real field agent, adopt it
into the ledger first, so the close is recorded:

```bash
python3 <agent_dir>/field.py register "<name>" "<pane_id>" "<harness>" "<task>"
python3 <agent_dir>/field.py ack "<name>" "<verdict>"
```

Name an unnamed agent before you adopt it:

```bash
herdr agent rename "<pane_id>" "<name>"
```

## Step 4: Remove worktrees BEFORE you close their panes

Do this before step 5, for any agent that holds a worktree.

List them from the source repo:

```bash
herdr worktree list --cwd "<the source repo>"
```

An entry with `"is_linked_worktree": true` is a field-agent checkout. Which
command clears it depends on whether it still has a workspace:

- `"open_workspace_id"` present: the pane was never moved. Remove it while the
  workspace exists, because the workspace closes with its last pane and
  `worktree remove` takes only `--workspace ID`; afterwards the command fails
  with `workspace_not_found`:

  ```bash
  herdr worktree remove --workspace <wN>
  ```

- `"open_workspace_id"` missing or null: the handler moved the pane into the
  room (`field-handler` step 4), or the workspace already closed. Only git
  clears it:

  ```bash
  git -C "<the source repo>" worktree remove "<path>"
  ```

Either way, remove only after the branch is merged or the user says so. The
branch survives in the source repository. The checkout does not.

## Step 5: Close the finished panes

```bash
FIELD_HANDLER_PANE=$SELF python3 <agent_dir>/field.py close "<name>"
```

The command re-checks the safety rules and refuses when any of these is true:

- The agent is `working`, `blocked` or `unknown`.
- The result is not acknowledged.
- The record holds a queued follow-up.
- The working directory holds uncommitted changes.
- The pane is the handler's own.

A refusal names its cause; fix the cause. `--force` closes the pane and
accepts the loss: for when the user asks for that specific pane, after you tell
them what it destroys.

Unpushed commits do **not** block a close. The command reports them, and the
branch survives in the repository.

## Step 6: Report

Give the user one table:

| Agent | Harness | Verdict | Action | Where the work is |
|-------|---------|---------|--------|-------------------|

State what you closed, what you held and why, and what needs their decision.
Name the branch or the file path for every result you keep.

## Paste-able version for another handler

Use this when the handler is pi, opencode or another harness without this
skill. Send it with `herdr agent prompt '<handler-name>' '<text>'`:

> Audit the agents you dispatched. Run
> `herdr agent list` and, for every agent whose `agent_status` is `idle`,
> `done` or `blocked`, run `herdr agent read <name> --source recent --lines 80`
> and read the result. Verify the work: check the files it names, and run the
> build or the tests when it touched code. Then report one table with the
> agent name, its pane id, its verdict and the path or branch that holds its
> output. Close a pane with `herdr pane close <pane_id>` only when you have
> read its result AND the work is complete AND `git -C <its cwd> status
> --porcelain` is empty. Do not close a pane that is `working` or `blocked`.
> Do not close a pane you did not start. List anything you did not close, with
> the reason.
