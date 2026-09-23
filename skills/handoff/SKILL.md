---
name: handoff
description: Generate a post-compact handoff prompt capturing current session state (done / in-flight / next / hard rules), save it as a new dated file outside the repo, then hand the user the /compact command to run. Use when the user says "handoff", "prep compact", "write a post-compact prompt", or context is running low mid-project.
---

# Handoff: post-compact continuation prompt

Compaction summaries are lossy. This skill writes the continuation prompt you
would want to receive after compaction, saves it durably, and tees up the
compact step. `/compact` is a built-in CLI command, not a tool, so the final
step is the user's.

Several agents often work at once, across repos and worktrees. Every handoff
is therefore its own file, named by time and topic, and belongs to the session
that wrote it.

## Where the file goes

```
${HANDOFF_DIR:-$HOME/.claude/handoffs}/<repo>/<YYYY-MM-DD-HHMM>-<slug>.md
```

- `<repo>`: the main repository's directory name, the same from every
  worktree: `basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"`.
  Outside a git repo, the basename of the working directory.
- `<slug>`: the project or topic in kebab-case (`conversion-dip-audit`), never
  a generic word like `handoff` or `session`.
- The directory sits outside every repo, so a handoff is never committed and
  survives worktree removal.
- Write with a fresh name only. If the path exists, append `-2`, `-3`.

## Steps

1. **Write the handoff** to a new path as above (`mkdir -p` the directory).
   Structure, in this order:
   - Front matter:
     ```
     ---
     created: 2026-09-23T14:05
     repo: agent-os
     worktree: /absolute/path/of/the/checkout
     branch: feat/example
     project: example-slug
     status: open
     ---
     ```
   - One line: project + phase + "mid-task on X" if applicable.
   - "Verify first": the checks the next session runs before acting, each
     with its expected result: `git -C <worktree> branch --show-current`
     prints `<branch>`; `git status --short` shows the named uncommitted
     files; each path in "Read first" exists. A mismatch means the world
     moved: the next session reports the drift to the user instead of acting.
   - "Read first": the 2-5 canonical files or notes that carry full state
     (specs, runbooks, snapshots, brain notes). Paths absolute.
   - "State": what is DONE and verified, key ids, names and URLs, where
     restore points and baselines live.
   - "Hard rules": safety rules, verified gotchas, and user preferences
     (nomenclature, writing rules) that must survive the compaction.
   - "IN-FLIGHT (resume here)": a checklist (`- [ ]`) of the exact next
     actions, with enough detail to resume without re-derivation, ending on
     a "Done when:" line that states the completion condition. PENDING USER
     DECISIONS go in as their own items so the next session asks instead of
     guessing.
   - "Then": the next 1-3 backlog items after the in-flight work.
2. **Durability check**: anything in context but not on disk (unverified
   findings, decisions, ids) goes into the handoff or the proper tracker
   (spec, STATUS file, brain, Notion) before compacting.
3. **Print the handoff** in the reply so the user can review it.
4. **Hand off the compact step.** Give the user the command with the file's
   absolute path:

   /compact Read <absolute path>. Run its Verify first checks, then set its status to consumed and resume from IN-FLIGHT.

   (Instructions passed to /compact steer the summary; the file is the real
   contract.)

## Resuming from a handoff

A session that resumes from a handoff runs its "Verify first" checks, then
sets the front matter `status: consumed`. That one field is the only edit a
session makes to a handoff it did not write. From there it works the
IN-FLIGHT checklist until the "Done when" line holds. When the resumed
session compacts in turn, it writes a new handoff.

## Rules

- The file is the source of truth, not the compaction summary; keep it
  self-contained (a fresh session with zero context must be able to act on it).
- Each handoff belongs to the session that wrote it. Write new files; leave
  other sessions' handoffs as they are, apart from marking one consumed when
  you resume from it.
- The file follows the user's writing rules and carries no secrets or tokens.
- Cleanup belongs to the close-out routine (for example `brain-wrap-session`):
  consumed handoffs are deleted, and open ones older than 14 days go to the
  user to keep or delete.
