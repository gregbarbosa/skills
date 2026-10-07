# Launching and briefing a field agent

The one-time launch mechanics that `field-agent` (steps 5 to 7) and
`field-handler` (steps 5 and 6) share. `<agent_dir>` is the `field-agent`
skill's directory, which holds `field.py` and `harnesses.json`. `<name>` is the
field agent's name, `m` is your handler name, `<pane_id>` is the pane the agent
runs in.

## Launch the harness

**Canonical harness** (`command` equals `kind`): one command starts it, names
it, and waits for readiness. `field-handler` puts its `model_flag` words before
the auto flag.

```bash
herdr agent start "<name>" --kind <kind> --pane "<pane_id>" -- [<model_flag words>] <auto_flag words>
```

On a name conflict, retry once with a numeric suffix. `agent start` needs a pane
sitting at a shell prompt and times out after 30 seconds. A startup dialog
returns `agent_not_ready` with the name still usable for `agent read` and
`agent send-keys`: clear the dialog, then continue.

**Wrapper harness** (`command` differs from `kind`: glm, ds): run it, wait for
herdr to detect it, wait for readiness, then name it:

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

If the launch fails, read the pane. A shell error (`command not found`, a stack
trace) is a failed launch: tell the user and stop. A TUI herdr has not detected
yet is fine: wait about 5 seconds and continue.

## Clear the startup dialogs

Read the pane (`herdr pane read "<pane_id>" --source visible --lines 30`), find
the line marked `❯`, and move to the option you want with `Down` or `Up` before
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

`Enter` also submits whatever sits in the input box, so a callback that arrived
during a dialog becomes the agent's next turn. After clearing a dialog, read
the pane and check what the agent is now working on.

## Check the permission mode

```bash
herdr pane read "<pane_id>" --source visible --lines 3
```

`⏵⏵ auto mode on` means the flag took. `⏸ manual mode on` means the agent will
stop at its first tool call: Haiku 4.5 ignores `--permission-mode auto`, which
is why Sonnet is the model floor.

## Register, then brief

Register before you prompt, so a crash between the two never leaves an
untracked agent:

```bash
python3 <agent_dir>/field.py register "<name>" "<pane_id>" "<harness>" \
  "<one-line task summary>" --branch "<branch or omit>" --cwd "<cwd>"
```

`field.py brief` renders the brief: your task text, your context, then the
reporting contract (identity, report command, the four report moments, the
rules). The contract wording was tuned against live agents; do not retype it.

Write two files in the scratchpad (or `/tmp`):

- **Task**: the request, with everything the agent must do.
- **Context** (optional): what you would tell a new teammate. Files to read
  first (absolute paths, the repo's `CLAUDE.md` or `AGENTS.md` first), facts
  already established, where credentials come from (a path or a command, never
  the value), and the conventions that apply (no em-dashes; whether it may
  `git add`, commit or change branch).

```bash
BRIEF=$(python3 <agent_dir>/field.py brief "<name>" --handler m \
  --task-file <task.md> --context-file <context.md> --budget <minutes> \
  --format <brief_format>)
herdr agent prompt "<name>" "$BRIEF" --wait --until working --timeout 15000
```

- `--format` is the harness entry's `brief_format`: `blocks` (tagged,
  multi-line) or `line` (` || ` separators). Missing means `blocks`.
- `--budget`: set it somewhat above the time you want spent; agents pace to
  finish inside it and usually finish early. Omit it without an estimate. It is
  advisory, so keep your own timeout for a hard stop.
- `--scoped` appends "Scope and read first; flag any irreversible change before
  you make it." to the task (`field-handler` always passes it).
- The brief reads the pane id from the ledger and stamps the start time.

## Read the prompt result

`--wait --until working` returns as soon as the agent is working, at once if it
already was.

| Outcome | Meaning | What you do |
|---------|---------|-------------|
| Exit 0, `agent_status` is `working` | The turn started. | Continue. |
| Exit 0, `agent_status` is `done` or `idle` | A short turn finished already. | Read the pane. |
| `agent_blocked` | A dialog was up. herdr sent NOTHING. | Clear the dialog, then prompt again. |
| `agent_prompt_stalled` | herdr saw no activity after it submitted. | Read the pane. |

On a stall, read the pane. A prompt sent to a busy claude-kind agent queues for
its next turn and is not stuck. Input-box text is stuck only when it matches
what you just sent; then send `herdr agent send-keys "<name>" Enter`, at most 3
times. If it never submits, tell the user rather than assuming it ran. Other
input-box text is usually Claude Code's prompt suggestion; leave it.
