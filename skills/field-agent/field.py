#!/usr/bin/env python3
"""field: handler-side tracking for herdr field agents.

The handler dispatches work to field agents in herdr panes. This script keeps
the record of those agents, and watches them for state changes.

Subcommands:
  register   Record a dispatched field agent in the ledger.
  watch      Poll herdr and print one line for each agent state change.
  catchup    Print every agent that is finished and not acknowledged.
  ack        Mark a field agent's result as read by the handler.
  status     Print the current roster as a table.
  note       Append a free-text note to a field agent's record.
  queue      Attach a follow-up task to a field agent's record.
  audit      Print a close or hold verdict for each live agent.
  close      Close one agent's pane, with the safety checks.

The ledger is ~/.claude/field/ledger.json. It survives a handler context
compaction, a handler restart, and a herdr pane id change.

This is the ONLY copy of this tool. The `field-handler` and `field-audit`
skills call it at this path. Do not copy it into another skill directory. A
second copy goes stale the moment this one changes.

Verified against herdr 0.9.0.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

FIELD_DIR = os.path.expanduser("~/.claude/field")
LEDGER = os.path.join(FIELD_DIR, "ledger.json")
WATCH_STATE = os.path.join(FIELD_DIR, "watch-state.json")

# The ledger lived in ~/.claude/fleet before the skills were renamed. Copy the
# records once, so a handler that resumes after the rename still sees the
# agents it dispatched.
LEGACY_DIR = os.path.expanduser("~/.claude/fleet")
MIGRATION_MARKER = os.path.join(FIELD_DIR, ".migrated-from-fleet")

# A field agent that reaches one of these states has stopped working.
# `idle` stays in this set on purpose. A claude or pi agent that finishes a
# turn and waits for input reports `idle`, and that is the only signal for an
# agent that finished without sending its callback. `emit` labels the event
# with the status name, so the handler sees IDLE, not DONE, and the skills
# triage the two differently: DONE means read the result, IDLE means read the
# pane, because the agent either finished quietly or stalled.
SETTLED = {"idle", "done", "blocked"}


def migrate_legacy_state():
    """Copy the pre-rename state into the new directory, exactly once.

    The gate is a marker file, NOT the ledger's existence. Gating on the
    ledger meant that a handler who archived or deleted ledger.json got the
    legacy records restored underneath them on the next command, and that a
    live watch-state.json could be overwritten by a stale one. Neither file is
    copied over an existing destination.
    """
    if os.path.exists(MIGRATION_MARKER) or not os.path.isdir(LEGACY_DIR):
        return
    os.makedirs(FIELD_DIR, exist_ok=True)
    for name in ("ledger.json", "watch-state.json"):
        src = os.path.join(LEGACY_DIR, name)
        dst = os.path.join(FIELD_DIR, name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
    with open(MIGRATION_MARKER, "w") as fh:
        fh.write(datetime.now(timezone.utc).isoformat(timespec="seconds") + "\n")


def handler_pane() -> str:
    """Return the handler's own pane id, so the tool never reports on it."""
    return (os.environ.get("FIELD_HANDLER_PANE")
            or os.environ.get("FLEET_COORDINATOR_PANE", ""))


def seen_entry(value):
    """Return (status, seq) for one watch-state entry.

    Older watch-state.json files stored a bare status string. Read both shapes,
    so an upgrade does not replay the whole roster as new events.
    """
    if isinstance(value, dict):
        return value.get("status"), value.get("seq")
    return value, None


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_note(rec, text):
    """Append a note, repairing a missing or null `notes` field first.

    A record written by an older version, or edited by hand, can carry no
    `notes` key at all. Appending blind raises and loses the note.
    """
    notes = rec.get("notes")
    if not isinstance(notes, list):
        notes = []
    notes.append({"at": now(), "text": text})
    rec["notes"] = notes


def read_json(path, default):
    """Return the parsed file, or `default` when it is unusable.

    A missing, unreadable, or malformed file must not stop the field tool.
    """
    try:
        with open(path) as fh:
            return json.load(fh)
    except (FileNotFoundError, IsADirectoryError, PermissionError,
            UnicodeDecodeError, json.JSONDecodeError, OSError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # The temp name carries the pid. The ledger and the watch state are GLOBAL
    # to the machine, so several handlers write them at the same time. A shared
    # temp name lets one process os.replace() the file that another process is
    # about to replace, and the loser dies with FileNotFoundError. That killed a
    # watch loop on 2026-09-10 with five watchers running.
    tmp = "%s.%d.tmp" % (path, os.getpid())
    try:
        with open(tmp, "w") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def herdr_agents():
    """Return the live agent list. Return None if herdr does not answer."""
    try:
        out = subprocess.run(
            ["herdr", "agent", "list"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)["result"]["agents"]
    except Exception:
        return None


def agent_key(agent) -> str:
    """Return a durable key for an agent.

    A pane id is not durable: `herdr pane move` gives the pane a new
    workspace-qualified id. The agent session id is durable for the life of
    the agent process. Prefer it.
    """
    session = agent.get("agent_session") or {}
    return session.get("value") or agent.get("pane_id") or "?"


def load_ledger():
    """Return the ledger, always with an `agents` dict.

    An external edit can leave a file that is valid JSON but the wrong shape.
    Every caller reads `ledger["agents"]`, so repair the shape here instead of
    raising in each caller.
    """
    data = read_json(LEDGER, {"agents": {}})
    if not isinstance(data, dict):
        return {"agents": {}}
    if not isinstance(data.get("agents"), dict):
        data["agents"] = {}
    # Drop any record value that is not a dict. One malformed entry, from a
    # hand edit or a partial write, must not crash every command that walks
    # the ledger.
    data["agents"] = {k: v for k, v in data["agents"].items()
                      if isinstance(v, dict)}
    return data


def find_record(ledger, handle, allow_pane=True):
    """Find a ledger record by name, session key, or pane id.

    `allow_pane` guards against a live agent inheriting a dead agent's record
    through a shared pane id. herdr 0.8.x recycled a pane id when its pane
    closed, which made that collision real. herdr 0.9.0 does not reuse a closed
    id, so the collision cannot happen there. The guard stays because it costs
    nothing and the ledger outlives any single herdr version: a caller that
    resolves a handle a human typed passes True for the convenience, and a
    caller that resolves a LIVE agent passes False.
    """
    agents = ledger["agents"]
    if handle in agents:
        return handle, agents[handle]

    # A name is unique among LIVE agents, but the ledger keeps finished ones,
    # so two records can share a name. Prefer an unacknowledged match: an
    # acknowledged record is already read, and the handler is almost always
    # reaching for the one that still needs attention. Warn when the choice
    # was ambiguous, so the handler can address the other by its key.
    by_name = [(k, r) for k, r in agents.items() if r.get("name") == handle]
    if by_name:
        unread = [(k, r) for k, r in by_name if not r.get("acknowledged")]
        chosen = (unread or by_name)[0]
        if len(by_name) > 1:
            print(f"note: {len(by_name)} ledger records are named {handle!r}; "
                  f"using key {chosen[0][:40]}. "
                  f"Address another by its full key.", file=sys.stderr)
        return chosen

    if allow_pane:
        for key, rec in agents.items():
            if rec.get("pane_id") == handle:
                return key, rec
    return None, None


# --------------------------------------------------------------------------
# register
# --------------------------------------------------------------------------

def cmd_register(args):
    """register <name> <pane_id> <harness> <task...> [--branch B] [--cwd D]"""
    if len(args) < 4:
        print("usage: register <name> <pane_id> <harness> <task...> "
              "[--branch B] [--cwd D]")
        print("the task summary is required; it is what the handler reads "
              "when it has lost track of the agent")
        sys.exit(1)
    name, pane_id, harness = args[0], args[1], args[2]
    rest = args[3:]
    branch = cwd = None
    task_words = []
    i = 0
    while i < len(rest):
        if rest[i] == "--branch" and i + 1 < len(rest):
            branch = rest[i + 1]; i += 2
        elif rest[i] == "--cwd" and i + 1 < len(rest):
            cwd = rest[i + 1]; i += 2
        else:
            task_words.append(rest[i]); i += 1

    # Wait briefly for herdr to assign a session id. Registering under a pane
    # id is the seed of the duplicate-record bug: `watch` later resolves the
    # same agent by its durable session id, finds the record by name, and has
    # to re-key it. Give detection a moment so the record starts on the right
    # key. Detection was measured at about 2 seconds.
    key = pane_id
    for _ in range(10):
        for agent in herdr_agents() or []:
            if agent.get("pane_id") == pane_id or agent.get("name") == name:
                key = agent_key(agent)
                break
        if key != pane_id:
            break
        time.sleep(1)

    ledger = load_ledger()
    record = {
        "name": name,
        "pane_id": pane_id,
        "harness": harness,
        "task": " ".join(task_words),
        "branch": branch,
        "cwd": cwd,
        "dispatched_at": now(),
        "status": "working",
        "acknowledged": False,
        "acked_at": None,
        "notes": [],
        "queued_followup": None,
    }

    # Re-registering an agent must not erase what the handler already recorded
    # about it. Only the dispatch fields are refreshed.
    existing = ledger["agents"].get(key)
    if isinstance(existing, dict):
        for field in ("acknowledged", "acked_at", "notes", "queued_followup",
                      "dispatched_at"):
            if field in existing:
                record[field] = existing[field]

    ledger["agents"][key] = record
    write_json(LEDGER, ledger)
    print(f"registered {name} ({pane_id}) key={key}")


# --------------------------------------------------------------------------
# watch: the event stream the handler's Monitor consumes
# --------------------------------------------------------------------------

def emit(kind, rec, agent, prev, extra=""):
    name = rec.get("name") if rec else (agent.get("name") if agent else "?")
    pane = agent.get("pane_id") if agent else (rec or {}).get("pane_id", "?")
    harness = (agent or {}).get("agent") or (rec or {}).get("harness", "?")
    task = (rec or {}).get("task", "")
    task = (task[:70] + "…") if len(task) > 70 else task
    tracked = "FIELD" if rec else "LOOSE"
    line = (f"[{tracked}] {kind} | name={name or '(unnamed)'} | pane={pane} | "
            f"harness={harness} | was={prev} | task={task}")
    if extra:
        line += f" | {extra}"
    print(line, flush=True)


def cmd_watch(args):
    """watch [--interval SECONDS] [--all]

    Print one line per agent state change. Only transitions print, so a quiet
    roster prints nothing. Without --all, only agents in the ledger and any
    blocked agent print.
    """
    interval = 15
    watch_all = "--all" in args
    if "--interval" in args:
        i = args.index("--interval")
        if i + 1 >= len(args):
            print("usage: watch [--interval SECONDS] [--all]")
            sys.exit(1)
        try:
            interval = int(args[i + 1])
        except ValueError:
            print(f"--interval needs a whole number of seconds, "
                  f"not {args[i + 1]!r}")
            sys.exit(1)
        if interval < 1:
            print("--interval must be at least 1 second")
            sys.exit(1)

    self_pane = handler_pane()
    seen = read_json(WATCH_STATE, {})

    while True:
        agents = herdr_agents()
        if agents is None:
            # herdr did not answer. Do not kill the watch; try again.
            time.sleep(interval)
            continue

        ledger = load_ledger()
        live_keys = set()

        for agent in agents:
            key = agent_key(agent)
            live_keys.add(key)
            pane = agent.get("pane_id")
            if pane and pane == self_pane:
                continue  # never report on the handler itself

            status = agent.get("agent_status", "unknown")
            seq = agent.get("state_change_seq")
            prev, prev_seq = seen_entry(seen.get(key))
            rec = ledger["agents"].get(key)
            if rec is None:
                # Resolve by NAME only, never by pane id. On herdr 0.8.x a
                # closed pane's id was handed to the next pane, so matching one
                # made an unrelated live agent inherit a dead record: the
                # watcher then reported that agent's every status flip under
                # the dead agent's name, and no acknowledgement could silence
                # it, because a settled entry cleared the flag again. herdr
                # 0.9.0 no longer reuses a closed id. Resolving by name only is
                # still correct, and it keeps the watcher safe on either
                # version. An unnamed live agent that no record claims is
                # simply not ours.
                name = agent.get("name")
                if name:
                    old_key, rec = find_record(ledger, name, allow_pane=False)
                    if rec is not None and old_key != key:
                        # RE-KEY the record onto the durable session id. Writing
                        # it back under `key` while leaving `old_key` in place
                        # produced TWO copies of one agent, and no ack could
                        # silence the pair: each settled transition cleared the
                        # flag on whichever copy it found.
                        del ledger["agents"][old_key]
                        ledger["agents"][key] = rec
                        write_json(LEDGER, ledger)

            if not watch_all and rec is None and status != "blocked":
                seen[key] = {"status": status, "seq": seq}
                continue

            if prev is None:
                # First sighting. Record it without firing, so arming the
                # watch does not replay the whole roster as new events.
                seen[key] = {"status": status, "seq": seq}
                continue

            # `state_change_seq` advances on every turn herdr observes. It is
            # the only way to see a turn that started and finished between two
            # polls, which a status comparison alone cannot detect.
            turned = (seq is not None and prev_seq is not None
                      and seq != prev_seq)

            if status != prev or turned:
                seen[key] = {"status": status, "seq": seq}
                if status in SETTLED:
                    # Three cases, and they are not the same:
                    #  - ENTRY into the settled set: a result arrived. Emit and
                    #    clear the ack.
                    #  - A NEW TURN while already settled (seq moved): the agent
                    #    ran again without the handler asking. Also new work, so
                    #    emit and clear the ack.
                    #  - A flip inside the settled set with no new turn: a
                    #    finished agent moves between done and idle on its own.
                    #    That is a badge change, not a result. It must NEVER
                    #    clear an acknowledgement a human already gave. It still
                    #    emits while the record is unread, because an unread
                    #    result is still waiting.
                    entered = prev not in SETTLED
                    new_turn = turned and not entered
                    unread = rec is None or not rec.get("acknowledged")
                    if entered or new_turn or unread:
                        emit(status.upper(), rec, agent, prev)
                    if rec is not None:
                        rec["status"] = status
                        if entered or new_turn:
                            rec["acknowledged"] = False
                        ledger["agents"][key] = rec
                        write_json(LEDGER, ledger)
                elif status == "working" and rec is not None:
                    rec["status"] = "working"
                    ledger["agents"][key] = rec
                    write_json(LEDGER, ledger)

        # An agent whose pane closed stops appearing in the list.
        for key in list(seen):
            if key not in live_keys:
                rec = ledger["agents"].get(key)
                if isinstance(rec, dict) and not rec.get("acknowledged"):
                    emit("GONE", rec, None, seen_entry(seen[key])[0],
                         "pane closed before the handler read it")
                    rec["status"] = "gone"
                    ledger["agents"][key] = rec
                    write_json(LEDGER, ledger)
                del seen[key]

        write_json(WATCH_STATE, seen)
        time.sleep(interval)


# --------------------------------------------------------------------------
# catchup / status / ack / note / queue
# --------------------------------------------------------------------------

def cmd_catchup(args):
    """catchup [--all]: print every settled, unacknowledged agent.

    Without --all, a loose agent (one no ledger record claims) prints only
    when it is `blocked`, which is the same filter `watch` applies. On a busy
    machine the unfiltered list is mostly the user's own idle sessions, and
    the real results scroll off the top.
    """
    show_all = "--all" in args
    agents = herdr_agents()
    if agents is None:
        # Never print a clear line here. The handler runs catchup to
        # recover missed results, and would read "clear" as "nothing waiting".
        print("[FIELD] error | herdr did not answer; the roster is UNKNOWN, "
              "not clear. Retry catchup once herdr responds.")
        sys.exit(1)

    self_pane = handler_pane()
    ledger = load_ledger()
    hits = 0
    live_keys = set()

    for agent in agents:
        key = agent_key(agent)
        live_keys.add(key)
        pane = agent.get("pane_id")
        if pane and pane == self_pane:
            continue  # never report on the handler itself
        status = agent.get("agent_status", "unknown")
        if status not in SETTLED:
            continue
        rec = ledger["agents"].get(key)
        if rec is None:
            name = agent.get("name")
            rec = find_record(ledger, name, allow_pane=False)[1] if name else None
        if rec and rec.get("acknowledged"):
            continue
        # Same filter as `watch`: a loose agent prints only when it is blocked.
        # Without this, the user's own idle sessions bury the real results.
        if not show_all and rec is None and status != "blocked":
            continue
        title = agent.get("terminal_title_stripped", "")
        emit(status.upper(), rec, agent, "unseen", f"title={title}")
        hits += 1

    # An agent can settle and then have its pane closed before the handler
    # arms the watch. It never appears in the live list, so the loop above
    # cannot see it. The ledger is the only remaining record.
    for key, rec in ledger["agents"].items():
        if key in live_keys or rec.get("acknowledged"):
            continue
        if rec.get("status") == "closed":
            continue
        emit("GONE", rec, None, rec.get("status", "unknown"),
             "pane is not live; the result was never read")
        hits += 1

    if hits == 0:
        print("[FIELD] clear | no settled unacknowledged agents")


def cmd_status(args):
    ledger = load_ledger()
    agents = herdr_agents()
    if agents is None:
        print("herdr did not answer; STATUS below is the last known ledger "
              "value, not live state.")
        agents = []
    live = {agent_key(a): a for a in agents}
    if not ledger["agents"]:
        print("field ledger is empty")
        return
    print(f"{'NAME':<24} {'PANE':<10} {'HARNESS':<9} {'STATUS':<9} {'ACK':<4} TASK")
    for key, rec in ledger["agents"].items():
        agent = live.get(key)
        status = agent.get("agent_status") if agent else rec.get("status", "gone")
        pane = agent.get("pane_id") if agent else rec.get("pane_id", "-")
        ack = "yes" if rec.get("acknowledged") else "NO"
        task = (rec.get("task") or "")[:44]
        print(f"{str(rec.get('name') or '?'):<24} {str(pane or '-'):<10} "
              f"{str(rec.get('harness') or '?'):<9} "
              f"{str(status or 'unknown'):<9} {ack:<4} {task}")
        if rec.get("queued_followup"):
            print(f"{'':<24} └─ queued: {rec['queued_followup'][:60]}")


def cmd_ack(args):
    if not args:
        print("usage: ack <name|pane> [verdict...]")
        sys.exit(1)
    ledger = load_ledger()
    key, rec = find_record(ledger, args[0])
    if rec is None:
        print(f"no ledger record for {args[0]}")
        sys.exit(1)
    rec["acknowledged"] = True
    rec["acked_at"] = now()
    if len(args) > 1:
        append_note(rec, " ".join(args[1:]))
    ledger["agents"][key] = rec
    write_json(LEDGER, ledger)
    print(f"acked {rec.get('name')}")


def cmd_note(args):
    if len(args) < 2:
        print("usage: note <name|pane> <text...>")
        sys.exit(1)
    ledger = load_ledger()
    key, rec = find_record(ledger, args[0])
    if rec is None:
        print(f"no ledger record for {args[0]}")
        sys.exit(1)
    append_note(rec, " ".join(args[1:]))
    ledger["agents"][key] = rec
    write_json(LEDGER, ledger)
    print(f"noted on {rec.get('name')}")


def cmd_queue(args):
    if len(args) < 2:
        print("usage: queue <name|pane> <follow-up task...>")
        sys.exit(1)
    ledger = load_ledger()
    key, rec = find_record(ledger, args[0])
    if rec is None:
        print(f"no ledger record for {args[0]}")
        sys.exit(1)
    rec["queued_followup"] = " ".join(args[1:])
    ledger["agents"][key] = rec
    write_json(LEDGER, ledger)
    print(f"queued follow-up for {rec.get('name')}")


# --------------------------------------------------------------------------
# audit / close
# --------------------------------------------------------------------------

def git_state(cwd):
    """Return (is_repo, dirty, branch, unpushed) for a directory."""
    if not cwd or not os.path.isdir(cwd):
        return (False, False, None, 0)
    def git(*a):
        try:
            r = subprocess.run(["git", "-C", cwd, *a],
                               capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None
    if git("rev-parse", "--is-inside-work-tree") != "true":
        return (False, False, None, 0)
    dirty = bool(git("status", "--porcelain"))
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    unpushed = 0
    counts = git("rev-list", "--count", "@{upstream}..HEAD")
    if counts and counts.isdigit():
        unpushed = int(counts)
    elif git("rev-parse", "--abbrev-ref", "@{upstream}") is None:
        # No upstream at all. Every commit on this branch is unpushed.
        c = git("rev-list", "--count", "HEAD")
        unpushed = -1 if c else 0
    return (True, dirty, branch, unpushed)


def closable(agent, rec, self_pane):
    """Decide whether a pane is safe to close. Return (verdict, reason)."""
    status = agent.get("agent_status", "unknown")
    pane = agent.get("pane_id")

    if pane == self_pane:
        return ("HOLD", "this is the handler's own pane")
    if status == "working":
        return ("HOLD", "still working")
    if status == "blocked":
        return ("HOLD", "blocked; it is waiting for an answer")
    if status == "unknown":
        return ("HOLD", "herdr cannot detect its status; read it by hand")
    if rec is None:
        return ("ASK", "not in the ledger; the handler did not dispatch it")
    if not rec.get("acknowledged"):
        return ("HOLD", "result not read yet; read and ack before closing")
    if rec.get("queued_followup"):
        return ("HOLD", f"has a queued follow-up: {rec['queued_followup'][:50]}")

    cwd = agent.get("cwd") or rec.get("cwd")
    is_repo, dirty, branch, unpushed = git_state(cwd)
    if is_repo and dirty:
        return ("HOLD", f"uncommitted changes in {cwd}")
    if is_repo and unpushed != 0:
        n = "all" if unpushed < 0 else unpushed
        return ("CLOSE", f"safe; note {n} unpushed commit(s) on {branch}; "
                         f"the branch survives a pane close")
    return ("CLOSE", "acknowledged, settled, working tree clean")


def cmd_audit(args):
    """audit [--include-loose]: print a close/hold verdict per agent."""
    self_pane = handler_pane()
    include_loose = "--include-loose" in args
    agents = herdr_agents()
    if agents is None:
        print("herdr did not answer; cannot audit")
        sys.exit(1)
    ledger = load_ledger()

    for agent in agents:
        key = agent_key(agent)
        rec = ledger["agents"].get(key)
        if rec is None:
            name = agent.get("name")
            rec = find_record(ledger, name, allow_pane=False)[1] if name else None
        if rec is None and not include_loose:
            continue
        verdict, reason = closable(agent, rec, self_pane)
        name = rec.get("name") if rec else (agent.get("name") or "(unnamed)")
        title = agent.get("terminal_title_stripped", "")[:52]
        print(f"{verdict:<6} | {str(name or '(unnamed)'):<22} | "
              f"{str(agent.get('pane_id') or '-'):<9} | "
              f"{str(agent.get('agent') or '-'):<9} | "
              f"{str(agent.get('agent_status') or 'unknown'):<8} | {reason}")
        print(f"       | cwd={agent.get('cwd')} | title={title}")
    print("\nCLOSE = safe to close. HOLD = do not close. ASK = confirm with the user.")


def cmd_close(args):
    """close <name|pane> [--force]: close one pane, with the safety checks."""
    if not args:
        print("usage: close <name|pane> [--force]")
        sys.exit(1)
    handle = args[0]
    force = "--force" in args
    self_pane = handler_pane()

    agents = herdr_agents()
    if agents is None:
        print("herdr did not answer; cannot close. The agent is UNKNOWN, not "
              "absent. Retry once herdr responds.")
        sys.exit(1)
    agent = None
    for a in agents:
        if a.get("name") == handle or a.get("pane_id") == handle:
            agent = a
            break
    if agent is None:
        print(f"no live agent named {handle}")
        sys.exit(1)

    ledger = load_ledger()
    key = agent_key(agent)
    rec = ledger["agents"].get(key)
    if rec is None:
        _, rec = find_record(ledger, handle)

    verdict, reason = closable(agent, rec, self_pane)
    if verdict != "CLOSE" and not force:
        print(f"REFUSED to close {handle}: {reason}")
        print("Fix the cause, or pass --force if you accept losing it.")
        sys.exit(1)

    pane = agent.get("pane_id")
    if not pane:
        print(f"live agent {handle} has no pane_id; cannot close it")
        sys.exit(1)
    out = subprocess.run(["herdr", "pane", "close", pane],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print(f"herdr refused to close {pane}: {out.stderr.strip()}")
        sys.exit(1)

    if rec is not None:
        rec["status"] = "closed"
        rec["closed_at"] = now()
        ledger["agents"][key] = rec
        write_json(LEDGER, ledger)
    print(f"closed {handle} ({pane}); {reason}")


COMMANDS = {
    "register": cmd_register, "watch": cmd_watch, "catchup": cmd_catchup,
    "ack": cmd_ack, "status": cmd_status, "note": cmd_note, "queue": cmd_queue,
    "audit": cmd_audit, "close": cmd_close,
}

if __name__ == "__main__":
    migrate_legacy_state()
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
