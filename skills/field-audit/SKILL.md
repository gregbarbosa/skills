---
name: field-audit
description: Use when the user asks to audit, sweep, review, tidy or clean up the agents and panes you dispatched, or to close panes whose work is done. Reads each field agent's result, verifies it, reports a verdict, then closes only the panes that are provably finished and safe. Requires herdr >= 0.9.0 and HERDR_ENV=1.
---

# field-audit: read the results, then close what is finished

Before you use this skill, check that `HERDR_ENV=1`. If it is not `1`, tell the
user that you do not run inside a herdr pane. Then stop.

This skill closes panes. A closed pane destroys unread output. Follow the order
below. Read first, close last.

Run `herdr --version`. This skill needs **0.9.0 or later**. On an earlier
version, tell the user to run `herdr update`. Then stop. Verified against herdr
0.9.0 (2026-09-08).

Related skills: **`field-agent`** dispatches one field agent.
**`field-handler`** runs a room of them. **`herdr`** documents the command
surface.

**These four skills are one suite.** `field-agent`, `field-handler`,
`field-audit` and `herdr` install together and depend on each other. Installing
one alone leaves it without its tools.

The ledger tool `field.py` lives in the **`field-agent`** skill's directory,
not this one. There is only one copy on purpose; a second copy goes stale.
Find it once and call it `<agent_dir>`:

```bash
find ~/.claude ~/.agents -maxdepth 5 -type d -path '*skills/field-agent' 2>/dev/null
```

Do not use a `*` glob in a plain `ls`; zsh aborts the whole command when one
glob does not match. `field.py` stores its state in `~/.claude/field/`.

The search covers BOTH roots on purpose. A single-agent install puts skills in
`~/.claude/skills`; a multi-agent install puts them in `~/.agents/skills`, and
Codex, Copilot, Gemini and pi read the second one. Searching only `~/.claude`
makes this skill fail on a perfectly normal multi-agent install.

If that `find` returns nothing, the suite is not fully installed. Do not
improvise a replacement and do not write your own ledger. Tell the user to run:

```bash
npx skills add gregbarbosa/skills -s '*' -g -y
```

Then stop.

## The rule

**Never close a pane whose result you have not read.** The point of a field
agent is its output. A close before a read throws away the work and leaves no
trace.

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

Then judge the work. Do not trust a summary line.

- Check that the files it names exist and hold the change.
- Run the build or the tests when the task touched code.
- Check the branch when the task was branch work.

Record the verdict, then acknowledge it. Acknowledgement is what makes the
agent eligible to close:

```bash
python3 <agent_dir>/field.py ack "<name>" "verified: 3 files changed, tests pass"
```

If the work is incomplete, do not acknowledge it. Prompt the agent to finish:

```bash
herdr agent prompt "<name>" "<what is missing>"
```

If the agent is `blocked`, read its question. Answer it when the brief makes
the answer unambiguous. Escalate to the user when the decision is theirs.

## Step 3: Handle the `ASK` agents

An `ASK` agent is not in your ledger. You did not dispatch it, or you
dispatched it in an earlier session that is now gone.

**Do not close an `ASK` agent on your own judgment.** It can be the user's own
interactive session. A pane sitting at the user's home directory, with a
title that names the user rather than a task, is almost certainly them
working, not a finished field agent.

For each `ASK` agent, read it, then tell the user what it holds and ask whether
to close it. Group them in one question. Do not ask once per agent.

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

**Order matters, and getting it wrong is not recoverable through herdr.** A
worktree workspace closes itself when its last pane closes. `worktree remove`
takes only `--workspace ID`, so once that workspace is gone the command fails
with `workspace_not_found` and herdr offers no other route. Measured on 0.9.0.

```bash
herdr worktree list --cwd "<the source repo>"
```

An entry with `"is_linked_worktree": true` is a field-agent checkout. One with
`"open_workspace_id": null` is already orphaned. Remove a live one while its
workspace still exists, after the branch is merged or the user says so:

```bash
herdr worktree remove --workspace <wN>
```

For an orphaned checkout, fall back to git:

```bash
git -C "<the source repo>" worktree remove "<path>"
```

The branch survives in the source repository. The checkout does not.

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

A refusal names its cause. Fix the cause. Do not reach for `--force`.

> `--force` closes the pane and accepts the loss. Use it only when the user
> asks for that specific pane, after you tell them what it destroys.

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
