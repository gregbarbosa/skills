# Operations: preconditions, recovery, concurrency, change protocol

Read when: starting a retrofit (preconditions), resuming/continuing one
(recovery), or changing an already-gated system (post-gate protocol).

## Preconditions

**One-time setup (first contact with the project):**

- **Git is the loop's spine.** No repo → `git init` + initial commit first
  (ask before doing this).
- **Verify the boot vector empirically.** Determine which file(s) THIS
  harness auto-loads (AGENTS.md? CLAUDE.md? both?). A file merely *existing*
  is not proof it's loaded — probe: add a distinctive marker line to the
  candidate file and ask a fresh subagent what boot instructions it sees
  (remove the marker after), or consult the harness's docs. The *convention
  file* is AGENTS.md; the *harness file* is whatever this harness loads; if
  they differ, make the harness file a one-line stub pointing at the
  convention file. If a boot file already exists with conflicting content,
  reconcile — surface contradictions to the user; never leave two disagreeing
  rules in the always-loaded file.

**Per-pass gate (EVERY pass, Pass 0 included):**

- `git status` first. Dirty tree with the user's uncommitted work → stop and
  ask them to commit/stash; never mix retrofit diffs into user WIP. Every
  mechanical pass must be revertible with one `git revert`.

## Recovery and resumption

- **Resuming any pass:** run `git status` first. A dirty tree means a
  suspected interrupted pass — diff it against the audit doc's "claimed" and
  "in progress" entries, then either finish the migration (the
  completion-test grep from the audit doc decides) or revert and restart the
  pass. Never begin a new pass
  over uncommitted retrofit work.
- **Trust but verify the audit doc:** before acting on it, spot-check its top
  claim against the tree (grep the pattern, count call sites). If reality
  disagrees — passes landed without doc updates, or code churned between
  passes — re-run a mini Pass 0 and fix the doc first.

## Concurrency

- Passes are serial by design. A session claims a pass by committing a
  "claimed: <pattern>, session <id>, started <time>" line to the audit doc
  BEFORE editing; a parallel/resuming session that sees a fresh claim works on
  something else or asks. This is distinct from the per-candidate
  "in progress: <pattern>, completion test: <grep>" tracker (SKILL.md,
  Pass 2..N) — both live under the audit doc's Claims section.
- Parallel work is safe only across independent (non-nested) patterns in
  separate worktrees, merged one at a time.

## Monorepos / workspaces

- One kit, as a shared package (that's rung-6 enforcement for free).
- Audit doc at the root with per-package sections.
- The root boot file carries the map + gate; each package's boot file is a
  2–3 line stub pointing at the root, so the chain works from any cwd.
- "Replace ALL call sites" is scoped per package per pass; the audit doc
  tracks which packages are migrated (a *tracked* partial migration is fine;
  an untracked one is the defect).

## Audit-doc template (`docs/system-audit.md`)

Fixed headings, created at Pass 0, updated every pass — a cold session can
only resume from a doc whose shape it can predict:

- **Inventory** — table: Pattern | Count (independent call sites) | Nests
  inside | Leaf?
- **Raw values → tokens** — candidates with counts
- **Rails** — derived rail set, the violation rubric used per rail, violations
- **Enforcement map (draft)** — current-state rungs 4–6 + target column
  (moves inline to the boot file at Pass N+1)
- **Claims** — "claimed:" pass claims + "in progress:" per-candidate
  completion tests (empty at Pass 0)
- **Pass log** — newest first: what was done, what remains, the single
  recommended next pass

## Post-gate change protocol (the steady state)

Any change to a component, token, or rule ships as ONE commit touching, in
order: (1) the component source / type surface, (2) its sibling `.md`,
(3) the pattern-table row, (4) the lint rule + its negative test re-verified,
(5) the enforcement-map section of the boot file, (6) the audit doc.

A lint failure caused by a deliberate, agreed rule change means updating the
rule in that same commit — the *sanctioned counterpart* to "never weaken";
without it, agents blocked by a stale rule weaken it informally. Extend the
docs-check to fail when a pattern-table entry names a nonexistent export
(table↔kit drift detection).

## The empirical orphan test

Asking yourself "could a new session find everything?" always answers yes.
Instead, spawn a fork/subagent with a fresh context: "You are a new session in
this repo. Using only auto-loaded files, name: the rules skill(s), the
pattern-table path, the audit doc, and the recommended next pass." The pass
isn't done until that agent answers correctly. Runs at the end of EVERY pass.
Before the gate exists (Pass 0..N) use the **reduced form** — name the audit
doc and the recommended next pass only; the full four-question test applies
from Pass N+1 on.

Mechanical backstop: extend the docs-check to verify every path mentioned in
the boot file exists (dead-pointer lint). Include "which harnesses actually
load this file?" — non-Claude harnesses may read different boot files and
don't discover `.claude/skills/`; add one-line pointer stubs per harness the
project actually uses.
