---
name: herdr
description: "Control herdr from inside it: workspaces, tabs and panes; start agents, read their output, address them by name, wait for their status. Use when HERDR_ENV=1."
---

# herdr: agent skill

Before you use this skill, check that `HERDR_ENV=1`. If it is not `1`, tell the
user that you do not run inside a herdr pane. Then stop.

Written for **herdr 0.9.0**. Run `herdr --version`; on a lower version tell the
user to run `herdr update`.

The client and the server update separately. After an update, check that both
moved before you rely on a new feature:

```bash
herdr status
```

Read `client.version`, `server.version` and `update.restart_needed`. A method
the server does not have is not permission to stop or restart the server.

The installed binary is the authority for syntax. Print a command group by
running it without a subcommand (`herdr agent`, `herdr pane`, `herdr workspace`,
`herdr tab`, `herdr worktree`, `herdr terminal`, `herdr notification`,
`herdr integration`, `herdr session`, `herdr machine`); bare `herdr` launches
the TUI.

herdr is a terminal agent multiplexer. It gives you workspaces, tabs and panes.
Each pane runs its own process: a shell, an agent, a server or a log stream.
You control all of it from the command line.

## Identifiers: read this before you use any id

**Ids are opaque handles: read every id from a live command.** Formats:

| Object | Format | Example |
|--------|--------|---------|
| Workspace | `w<N>` | `w15`, `w1B` |
| Tab | `w<N>:t<M>` | `w15:t5`, `w1B:tB` |
| Pane | `w<N>:p<M>` | `w15:p9`, `w15:pG` |

**A closed tab or pane id is not reused**, so a stale pane id resolves to
nothing rather than to the wrong agent. (herdr 0.8.x recycled ids; a ledger it
wrote can still hold an id a live pane now uses.)

**A pane id still changes.** `herdr pane move` into another workspace gives the
pane a new workspace-qualified id. Continue with
`.result.move_result.pane.pane_id`, or with the agent's name.

**An agent has three handles. Their durability is different:**

| Handle | Durable? | Use it for |
|--------|----------|-----------|
| `name` | Yes, until you rename it, or the agent exits or is replaced | Every message you send to an agent |
| `agent_session.value` | Yes, for the life of the agent process | A ledger key that must survive a pane change |
| `pane_id` | **No**: it changes on `pane move`, and dies with the pane | One immediate command, and nothing more |

**Rule: address an agent by its name.** Every `herdr agent` subcommand accepts
a name in the `<TARGET>` position:

```bash
herdr agent get qring-teardown          # works
herdr agent prompt qring-teardown "…"   # works
herdr agent read qring-teardown         # works
```

Give each agent a name at start time, or set one later:

```bash
herdr agent rename w15:p3 qring-teardown
```

An agent without a name is hard to find again. Name every agent you start.

`$HERDR_PANE_ID` is set at shell start. It goes stale after a pane move. Read
your own pane id live instead:

```bash
herdr pane current --current | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])'
```

## Agent status

herdr detects agent status. The field is `agent_status`:

| Status | Meaning |
|--------|---------|
| `working` | The agent runs a turn now. |
| `idle` | The agent finished and waits for input. |
| `done` | The agent finished and nothing has marked the pane seen. |
| `blocked` | herdr recognized an approval or question dialog. |
| `unknown` | herdr cannot classify the pane. It does NOT prove completion. |

`idle`, `done` and `blocked` all mean the agent stopped work; treat all three as
"this agent needs attention". Harnesses differ: pi ends at `done`; opencode has
been seen at `working` after it finished.

`idle` and `done` differ only by the server's seen flag. An explicit focus
command (`agent focus`, `agent prompt`) marks the target seen and flips `done`
to `idle`. A read does not. Each TUI client tracks completions separately, so
the Done badge you see in the app can differ from what the CLI reports.

## The agent commands

```bash
herdr agent list                    # all agents, as JSON
herdr agent get <TARGET>            # one agent, as JSON
herdr agent read <TARGET> --lines 60   # its terminal output
herdr agent prompt <TARGET> "<TEXT>"   # submit a prompt, then Enter
herdr agent send-keys <TARGET> Enter
herdr agent rename <TARGET> <NAME>
herdr agent focus <TARGET>
herdr agent wait <TARGET> --until done --timeout 60000
herdr agent start <NAME> --kind <KIND> --pane <ID> -- <agent args>
herdr agent explain <TARGET>        # why herdr detects the status it does
```

### agent start

```bash
herdr agent start api-review --kind claude --pane w15:p7 -- --permission-mode auto
```

The pane must already exist and must sit at an interactive shell prompt, with
the shell in the foreground and no command, editor or agent running.
**`agent start` never creates, splits or moves layout.** Make the pane first
with `pane split`, `tab create` or `worktree create`.

The command returns success only after herdr detects the agent and the agent
accepts input. Startup defaults to a 30000 ms timeout. If a dialog blocks the
agent during startup, herdr returns `agent_not_ready` at once, but the name
still works for `agent read` and `agent send-keys`. Clear the dialog, then wait
for `idle` before you prompt.

`<NAME>` must match `[a-z][a-z0-9_-]{0,31}` and must be unique among live
agents. On a name conflict, add a numeric suffix and retry once. A name follows
the pane's current occupant, and clears when that agent exits or is replaced.

A harness flag can fail to take (Haiku 4.5 ignores `--permission-mode auto`).
Read the status line after `agent start`: `⏵⏵ auto mode on` versus
`⏸ manual mode on`.

Valid kinds: `pi`, `claude`, `codex`, `gemini`, `cursor`, `devin`, `agy`,
`cline`, `omp`, `mastracode`, `opencode`, `copilot`, `kimi`, `kiro`, `droid`,
`amp`, `grok`, `hermes`, `kilo`, `qodercli`, `qwen`, `maki`, `muse`.

### agent prompt

`agent prompt` sends the text and the Enter key in one request. It respects
bracketed-paste mode. Use it instead of `send-text` and a separate `send-keys`.

```bash
herdr agent prompt api-review "read src/api and list the untested paths" --wait --until working --timeout 15000
```

Behaviour to plan for:

- If the agent is `blocked`, herdr rejects the prompt with `agent_blocked`. It
  sends no input. Read the pane and clear the block first.
- After it submits, herdr waits up to 5000 ms to observe `working` or
  `blocked`. If it observes neither, it returns `agent_prompt_stalled`.
- `--wait` does not track turns. If the agent already works, `--wait` can match
  the end of the turn that already runs.

**Which wait to use:**

| Form | Returns when |
|------|--------------|
| `--wait --until working` | The agent is working; at once if it already was. |
| `--wait` (no `--until`) | The agent settles: `idle`, `done` or `blocked`. |

`--until working` dispatches and moves on; plain `--wait` blocks until the turn
finishes. A prompt sent to a busy claude-kind agent queues for its next turn.

On `agent_prompt_stalled`, read the pane. If the text sits in the input box and
matches what you just sent, send `herdr agent send-keys <TARGET> Enter`, at
most 3 times. If it never submits, tell the user rather than assuming it ran.

### agent wait

```bash
herdr agent wait api-review --until done --timeout 120000
```

Without `--until`, it matches `idle`, `done` or `blocked`. Without `--timeout`,
it waits forever.

> **`agent wait` blocks your own turn**, so it fits a short, known wait. To
> supervise a long task or several agents, use the `field-agent` skill's watch
> loop.

## Panes

```bash
herdr pane list
herdr pane current
herdr pane read w15:p3 --source recent --lines 50
herdr pane split w15:p2 --direction right --no-focus
herdr pane run w15:p3 "npm run dev"
herdr pane send-text w15:p3 "text with no Enter"
herdr pane send-keys w15:p3 Enter
herdr pane close w15:p3
herdr pane wait-output w15:p3 --match "ready on port 3000" --timeout 30000
herdr pane wait-output w15:p3 --regex "server.*ready" --timeout 30000
```

`--source` accepts `visible`, `recent`, `recent-unwrapped` and `detection`. Use
`recent-unwrapped` when a soft wrap breaks a match. `pane read` prints text.
`pane read --format ansi` prints an ANSI snapshot.

> `--match` and `--regex` are alternatives; `--regex` takes the pattern as its
> value. `herdr wait output` and `herdr wait agent-status` no longer exist; use
> `pane wait-output` and `agent wait`.

## Tabs and workspaces

```bash
herdr workspace list
herdr workspace create --cwd /path/to/project --label "api server" --no-focus
herdr workspace focus w2
herdr workspace close w2            # add --group to also close linked worktrees
herdr tab list --workspace w15
herdr tab create --workspace w15 --label "logs"
herdr tab focus w15:t2
herdr tab close w15:t2
```

`--no-focus` keeps your own pane focused. Each returned object carries its id
inside it:

- `workspace create` returns `.result.workspace`, `.result.tab`,
  `.result.root_pane`. The ids are `.result.workspace.workspace_id`,
  `.result.tab.tab_id`, `.result.root_pane.pane_id`.
- `tab create` returns `.result.tab` and `.result.root_pane`, same shape.
- `pane split` returns `.result.pane`; the id is `.result.pane.pane_id`.

## Git worktrees

```bash
herdr worktree create --branch "fix/parser-overflow" --label "parser fix" --base main --no-focus
herdr worktree list
herdr worktree remove --workspace w17
```

`worktree create` makes the git worktree and a new workspace together. Its
response holds `.result.root_pane.pane_id` and `.result.worktree.path`. Pass
`--no-focus` unless the user asked to switch context. That new
workspace is LINKED to the one you created it from, so a plain
`workspace close` on the parent fails with `workspace_group_close_required`.
Use `workspace close <wN> --group` only when you mean to close every linked
workspace too.

Use a worktree when the task changes branches. A pane in the same directory
that runs `git checkout -b` moves **your** branch too.

## Notifications

```bash
herdr notification show "Build finished" --body "3 tests failed" --sound done
```

`--sound` accepts `none`, `done` and `request`.

## Recipes

### Start a server and wait for it

```bash
PANE=$(herdr pane split w15:p2 --direction right --no-focus \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')
herdr pane run "$PANE" "npm run dev"
herdr pane wait-output "$PANE" --match "ready" --timeout 30000
herdr pane read "$PANE" --source recent --lines 20
```

### See what every agent does now

```bash
herdr agent list | python3 -c '
import sys,json
for a in json.load(sys.stdin)["result"]["agents"]:
    print(f"{a[\"pane_id\"]:<9} {a.get(\"name\") or \"-\":<20} {a.get(\"agent\") or \"-\":<9} {a[\"agent_status\"]}")
'
```

### Read a finished agent

```bash
herdr agent read api-review --source recent --lines 80
```

## Related

To dispatch work to one new agent and supervise it, use the **`field-agent`**
skill; several on one theme, **`field-handler`**; reading results and closing
finished panes, **`field-audit`**. They add the naming contract, the field
ledger and the watch loop.

## Notes

- These commands print JSON: `workspace list`, `workspace create`, `tab list`,
  `tab create`, `tab get`, `tab focus`, `tab rename`, `tab close`, `pane list`,
  `pane current`, `pane get`, `pane split`, `pane wait-output`, `agent list`,
  `agent get`, `agent wait`, `worktree list`, `worktree create`.
- These commands print nothing on success: `pane send-text`, `pane send-keys`,
  `pane run`.
- `pane read` and `agent read` print text, not JSON.
- Use `pane read` for output that exists now. Use `pane wait-output` for output
  that you expect next.
- For the raw socket protocol, read https://herdr.dev/docs/socket-api/.
