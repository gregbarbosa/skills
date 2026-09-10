---
name: herdr
description: "The semantics herdr's own skill leaves out: agent status vocabulary, the three agent handles, the dispatch and wait idioms, naming, the permission-mode check, worktree removal order, which commands print JSON. Use with `herdr --skill` when HERDR_ENV=1."
---

# herdr: what the bundled skill leaves out

Before you use this skill, check that `HERDR_ENV=1`. If it is not `1`, tell the
user that you do not run inside a herdr pane. Then stop.

Run `herdr --skill` first. It prints the command surface for the installed
version, so it is never stale. Print a command group's syntax by running it
without a subcommand (`herdr agent`, `herdr pane`, `herdr worktree`); bare
`herdr` launches the TUI. This skill carries only what those two leave out.

## Handles

Ids are opaque: read every id from a live command. A closed tab or pane id is
not reused, so a stale pane id resolves to nothing rather than to the wrong
agent. `herdr pane move` into another workspace gives the pane a new id;
continue with `.result.move_result.pane.pane_id`, or with the agent's name.

An agent has three handles of different durability:

| Handle | Durable? | Use it for |
|--------|----------|-----------|
| `name` | Yes, until you rename it, or the agent exits or is replaced | Every message you send to an agent |
| `agent_session.value` | Yes, for the life of the agent process | A ledger key that must survive a pane change |
| `pane_id` | No: it changes on `pane move`, and dies with the pane | One immediate command, and nothing more |

Every `herdr agent` subcommand takes a name in the `<TARGET>` position. Name
every agent you start (`agent start <NAME>`, or `agent rename <pane> <NAME>`
later); a name must match `[a-z][a-z0-9_-]{0,31}` and be unique among live
agents. An unnamed agent record has no `name` key, so read names with
`.get("name")`.

`$HERDR_PANE_ID` is set at shell start and goes stale after a pane move. Read
your own pane id live:

```bash
herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])'
```

## Agent status

| `agent_status` | Meaning |
|--------|---------|
| `working` | The agent runs a turn now. |
| `idle` | The agent finished and waits for input. |
| `done` | The agent finished and nothing has marked the pane seen. |
| `blocked` | herdr recognized an approval or question dialog. |
| `unknown` | herdr cannot classify the pane. It does not prove completion. |

`idle`, `done` and `blocked` all mean the agent stopped work; treat all three
as "needs attention". `idle` and `done` differ only by the server's seen flag:
`agent focus` and `agent prompt` mark the target seen and flip `done` to
`idle`, a read does not, and each TUI client tracks completions separately, so
the app's Done badge can differ from the CLI. Harnesses differ too: pi ends at
`done`; opencode has been seen at `working` after it finished.

## Starting an agent

`agent start` returns only after the agent accepts input. A startup dialog
returns `agent_not_ready` with the name still usable for `agent read` and
`agent send-keys`; clear the dialog, then wait for `idle` before you prompt. On
a name conflict, add a numeric suffix and retry once.

A harness flag can fail to take (Haiku 4.5 ignores `--permission-mode auto`).
Read the status line after the start: `⏵⏵ auto mode on` versus
`⏸ manual mode on`.

## Prompting and waiting

`agent prompt` sends the text and Enter in one request and respects bracketed
paste, so a multi-line prompt arrives intact. Behaviour to plan for:

- A `blocked` agent rejects the prompt with `agent_blocked` and receives no
  input; read the pane and clear the block first.
- After submitting, herdr waits up to 5000 ms to observe `working` or
  `blocked`; otherwise it returns `agent_prompt_stalled`.
- `--wait` does not track turns: on an agent that is already working it can
  match the end of the running turn.

| Form | Returns when |
|------|--------------|
| `--wait --until working` | The agent is working; at once if it already was. |
| `--wait` (no `--until`) | The agent settles: `idle`, `done` or `blocked`. |

`--until working` dispatches and moves on; plain `--wait` blocks until the turn
finishes. A prompt to a busy claude-kind agent queues for its next turn.

On `agent_prompt_stalled`, read the pane. If the text sits in the input box and
matches what you just sent, send `herdr agent send-keys <TARGET> Enter`, at
most 3 times. If it never submits, tell the user rather than assuming it ran.
Text in an input box that does not match what you sent is usually Claude
Code's prompt suggestion; leave it.

`agent wait` blocks your own turn, so it fits a short, known wait. To supervise
a long task or several agents, use the `field-agent` skill's watch loop.

## Worktrees

`worktree create` makes the git worktree and a new workspace together, linked
to the workspace you created it from; a plain `workspace close` on the parent
fails with `workspace_group_close_required`, and `--group` closes every linked
workspace. Its response holds `.result.root_pane.pane_id` and
`.result.worktree.path`.

To keep a worktree agent beside you instead, move its root pane into a tab of
your own workspace: `herdr pane move <root_pane> --tab <tab> --split right
--target-pane <pane>` (or `--new-tab --workspace <ws>` for a tab of its own).
The pane gets a new id and the linked workspace closes itself.

A worktree workspace closes with its last pane, and `worktree remove` takes
only `--workspace <id>`, so remove the worktree before its pane closes;
afterwards, and for any moved pane, only `git worktree remove <path>` clears
the checkout. The branch survives either way.

A pane in your own directory that runs `git checkout -b` moves your branch
too, so branch work belongs in a worktree.

## Output shapes

- These print JSON: `workspace list`, `workspace create`, `tab list`,
  `tab create`, `tab get`, `tab focus`, `tab rename`, `tab close`, `pane list`,
  `pane current`, `pane get`, `pane split`, `pane wait-output`, `agent list`,
  `agent get`, `agent wait`, `worktree list`, `worktree create`.
- These print nothing on success: `pane send-text`, `pane send-keys`,
  `pane run`.
- `pane read` and `agent read` print text. `--source` accepts `visible`,
  `recent`, `recent-unwrapped` (for a match a soft wrap breaks) and `detection`.
- Created objects carry their id inside: `.result.tab.tab_id`,
  `.result.root_pane.pane_id`, `.result.pane.pane_id`,
  `.result.workspace.workspace_id`.
- `herdr wait output` and `herdr wait agent-status` no longer exist; use
  `pane wait-output` and `agent wait`.

## Related

`field-agent` dispatches one agent with a reporting contract, a ledger and a
watch loop; `field-handler` runs several on one theme; `field-audit` reads the
results and closes finished panes.
