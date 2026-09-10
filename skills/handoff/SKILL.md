---
name: handoff
description: Generate a post-compact handoff prompt capturing current session state (done / in-flight / next / hard rules), save it durably, then hand the user the /compact command to run. Use when the user says "handoff", "prep compact", "write a post-compact prompt", or context is running low mid-project.
---

# Handoff: post-compact continuation prompt

Compaction summaries are lossy. This skill writes the continuation prompt you
would want to receive after compaction, saves it durably, and tees up the
compact step. `/compact` is a built-in CLI command, not a tool, so the final
step is the user's.

## Steps

1. **Write the handoff prompt** to `tasks/handoff-prompt.md` in the project
   (create `tasks/` if needed; if the project has no tasks dir convention, use
   the repo root). Structure, in this order:
   - One line: project + phase + "mid-task on X" if applicable.
   - "Read first": the 2-5 canonical files/notes that carry full state
     (PRDs, runbooks, snapshots, brain notes). Paths must be exact.
   - "State": what is DONE and verified, key ids/names/URLs, where restore
     points and baselines live.
   - "Hard rules": any safety rules, verified gotchas, and user preferences
     (nomenclature, writing rules) that MUST survive the compaction.
   - "IN-FLIGHT TASK (resume here)": the exact next actions, numbered, with
     enough detail to resume without re-derivation. Include any PENDING USER
     DECISIONS explicitly so the next session asks instead of guessing.
   - "Then": the next 1-3 backlog items after the in-flight task.
2. **Durability check**: anything in context but not on disk (unverified
   findings, decisions, ids) gets written into the prompt file or the proper
   tracker (PRD, brain, Notion) BEFORE compacting.
3. **Print the prompt** in the reply so the user can review it.
4. **Hand off the compact step.** Tell the user to run:

   /compact Read tasks/handoff-prompt.md and follow it exactly.

   (Passing instructions to /compact steers the summary; the file is the real
   contract. After compaction, the next session reads the file and resumes.)

## Rules

- The file is the source of truth, not the compaction summary; keep it
  self-contained (a fresh session with zero context must be able to act on it).
- The file follows the user's writing rules (for Greg: no em-dashes, "Avulux"
  and "Avulux Adapt" nomenclature) and carries no secrets or tokens.
- Overwrite the previous handoff-prompt.md; it is a living scratch document,
  and a stale handoff is worse than none.
