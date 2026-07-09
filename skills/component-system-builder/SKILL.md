---
name: component-system-builder
description: Use when standing up a Glaze-style closed-world component + agent-rules system for a platform (Electron, Astro, iOS/SwiftUI, …), OR when auditing an existing project to retrofit one — extracting a component kit, tokens, pattern table, and rules from code that grew without them. The architecture that makes AI-generated apps consistent by removing choices.
---

# Component System Builder

Build the machinery that makes an AI agent produce consistent, polished apps
on a given platform. The principle: **consistency comes from removing choices,
not from model skill.** Reference implementation: Raycast Glaze. If the project
you are in ships its own teardown of that reference, read it; otherwise skip it,
do not search — the skill is self-contained without it.

## Reference files (read on demand, in this skill's directory)

- `references/operations.md` — preconditions, recovery/resumption,
  concurrency, monorepos, the post-gate change protocol, the empirical orphan
  test. Read before starting, resuming, or changing a system.
- `references/enforcement.md` — the enforcement map, platform mechanism
  table, the red-teamed rung-5 recipe, sanctioned-exception & lore-in-docs
  patterns. Read at Pass 0 (draft the map into the audit doc), Pass N+1
  (the map moves inline into the boot file), and Pass N+2 (tooling).
- `references/runtime-discipline.md` — Glaze's "muscles": pattern-skill
  anatomy beyond the table, the validation loop, delegation economics,
  just-in-time skill invocation, memory schema, docs-reader invariants,
  theming/compositing lore. Read when writing artifacts 2–6 (§7 BEFORE
  authoring any seed or judging raw values).

## Two modes

- **Green-field**: start from the platform scaffold/template (artifact 6 —
  in Glaze every app BEGINS as the template; the agent's job is transforming
  it, never wiring from scratch), then build artifacts 1–5. Green-field has
  no passes to cue the reference reads, so: operations.md preconditions
  BEFORE scaffolding (boot-vector verification especially); draft the
  enforcement map BEFORE artifact 1 (type surfaces are rung 4); run the
  orphan test after EACH artifact lands.
- **Retrofit (existing project)**: run the audit loop below — the artifacts
  are the *target state*. Expect multiple passes.

## Retrofit audit loop

Pass semantics: **one pass = one merge-able commit** (audit-doc update
included in the SAME commit). "Stop and summarize" = checkpoint (commit +
audit doc + report), not necessarily end-session; run more passes in one
session when asked — a cold session resumes from the audit doc either way
(resuming? read Recovery in `references/operations.md` FIRST: `git status`
before trusting the audit doc). Before EVERY pass — Pass 0 included — run the
per-pass gate in `references/operations.md`; run its one-time setup (git
spine, boot-vector verification) on first contact with the project.

**Pass 0 — inventory (no source edits; still a pass).** It ends with a
commit adding the audit doc AND the boot-file pointer to it. A **pattern** is
a named, reusable UI intent (Card, Stat, MediaRow) expressed in markup — NOT
a repeated utility-class cluster (`flex items-center gap-2` feeds (b), not
(a)). Produce `docs/system-audit.md` (template in
`references/operations.md`) with: (a) patterns ≥2× ranked by count of
independent call sites (nested candidates counted at their own level),
**recording which candidates nest inside which**; (b) raw values that should
be tokens — hex/rgb literals AND palette utilities like `bg-blue-500`; read
`references/runtime-discipline.md` §7 first; (c) platform-rail violations
(derive the rail set — artifact 4 has starters; record the rubric you used
per rail); (d) the draft **enforcement map** — a CURRENT-state snapshot
(mostly "none — falls back" is honest) plus a target column; it lives in the
audit doc until Pass N+1 moves it inline into the boot file
(`references/enforcement.md`).

**Pass 1 — tokens.** Compositing lore first (`references/runtime-discipline.md`
§7 — a parity diff cannot catch under-saturated seeds). Seeds + semantic
tokens (artifact 2); mechanical
replacement, no extraction. Parity is provable, not eyeballed: one raw value →
one token first (output provably unchanged); merge near-duplicates only in a
separate reviewed commit. Web/Astro: diff built output — text-identical is the
proof. Compiled UI: build + snapshot tests/screenshots.

**Pass 2..N — componentize.** Rank by count but **extract leaves before
containers** (extracting a parent first freezes raw markup inside the kit).
Per candidate: record "in progress: <pattern>, completion test: <grep>" in the
audit doc BEFORE editing; extract; write its `.md` (artifact 1 sections);
replace ALL call sites in the same pass (scoped per package in workspaces,
tracked in the audit doc); verify; commit.

**Pass N+1 — build the gate.** Only once the kit covers the real patterns:
pattern
table + rules skill + tiny always-on constraints file. Until artifact 5's
symbol map exists, **the kit's public index IS the interim symbol map** — say
so in the gate text.

**Pass N+2 — mechanical enforcement.** Climb the ladder
(`references/enforcement.md`). Automate a rule only after the tree already
satisfies it, or the first CI run is a wall of noise.

**Every pass ends with:** what was done, what remains, the single recommended
next pass — written into the audit doc, plus the orphan test
(`references/operations.md`) — EVERY pass, not just artifact-creating ones;
before the gate exists, use its reduced form.

## The six artifacts

### 1. Component kit with docs beside source
Every component ships `<name>.{tsx|astro|swift}` **plus `<name>.md` beside
it**. The `.md` is decision guidance, not API reference — required sections:
**When to Use** (one bullet per variant, phrased as rules — "`accent`: the one
primary action per screen"), **Usage Patterns** (canonical snippets incl.
composition), **Pitfalls** (what breaks when you guess). Components consume
semantic tokens only.

### 2. Seed-variable theming
~10 seeds drive everything (Glaze: `--bg`, `--bg-secondary`, `--fg`,
`--theme-accent`, `--selection`, + support colors); every semantic token is
*computed* from seeds (`text-secondary` = fg @ 60%, `bg-control` = fg @ 10%).
Acceptance test: a full rebrand = a ~10-line seed override per appearance.
Before authoring seeds, capture the platform's compositing lore
(`references/runtime-discipline.md` §7) — e.g. Glaze's light seeds needed
~2.5× saturation because they composite at 40% over window material.

### 3. Pattern-table skill (highest leverage — do not skip)
- **The Gate**: (1) pattern in the table → you MUST use that component;
  (2) read its `.md` before writing it — never guess props; (3) not in the
  table → prove non-existence (symbol map; until it exists, the kit's public
  index) and only then write custom, tokens only. **"Writing custom for
  something that has a component is a defect."**
- **The table**: every UI pattern → component(s) → doc path (an existence
  proof that can't route to the doc is half a gate). Categories: Layout /
  Forms / Actions / Overlays / Feedback / Data Display.
- **The table is only a third of the real skill.** It must also carry the
  never-hand-roll element mapping, selection-decision tests, anti-default
  styling rules, layout invariants, and a closing verification checklist —
  see `references/runtime-discipline.md` §1. A gate without these still
  produces web-shaped UI in custom markup.

### 4. Rules skills + tiny always-on context
Always-on boot file: **constraints + pointers only, ~6KB** — edit boundaries,
forbidden imports/APIs, the inline enforcement map, skill-invocation rule.
Per-concern skills on demand; frontend rules = the platform's rails as hard
prohibitions with a checklist (starter examples — derive the full set per
platform: Electron/React: URL-driven state, React Query over `useEffect`,
kit-only components, exact-dimension skeletons, native vibrancy not CSS blur.
Astro: islands-only interactivity, content collections, zero client JS by
default. SwiftUI: value-type state + Observation, NavigationStack routing).
The rules skill MUST include the **validation loop**
(`references/runtime-discipline.md` §2) — verify-what-you-built is a separate
mechanism from rule rigidity. Optional at scale: a task-recipe guide with
decision trees first — affordable only with a guide line-number index
(`references/runtime-discipline.md` §6).

### 5. Context-economy plumbing
- **Docs-reader fork skill** (isolated context, cheap model, Read-only, exact
  paths in → API card out). Invariant: **never trim props/variants** —
  condense prose only (`references/runtime-discipline.md` §6). Fire it in the
  background; block only when writing component code.
- **Symbol map**: generated index answering "does X exist, where's its doc."
- **Per-project memory**: `PROJECT-CONTEXT.md` overwrite-in-place with a
  schema + update-after-every-change rule; `PROJECT-HISTORY.md` append-only
  (`references/runtime-discipline.md` §5 — in a file-based replica the AGENT
  owns both; mandate it in the boot file).

### 6. Scaffold + orchestration
- Template repo per platform (`npx degit <user>/<template> <new>`). For
  green-field this is where you START (see Two modes), not an afterthought:
  the template guarantees the wiring before the agent types a line.
- Architect subagents: thin prompts — role (2 lines) + "invoke your rules
  skill first" + output contract (≤200 words, Files/Decisions/Issues only).
  **Default is NO delegation** — subagents are cache-cold and expensive; see
  the delegation gate + handoff mechanics in
  `references/runtime-discipline.md` §3.

## The enforcement ladder (summary)

Rigidity = placing every rule as HIGH on this ladder as the platform allows;
each rung up converts "asked to follow" into "can't break":
1 prose → 2 checklists → 3 The Gate + defect framing → 4 closed type surfaces
→ 5 lint/CI failure → 6 physically blocked (module boundaries, unwritable
paths, `--no-inline-config`).

Before building rungs 4–6, draft the **enforcement map** (which mechanism
exists on THIS platform, per rung — inline in the boot file) and honor its
honesty rules: never invent enforcement the toolchain can't run; unenforceable
rules are listed as "checked by review, not tooling"; **the enforcement config
is itself a protected artifact**; and **rigidity is a dial** — the defect is
an undocumented gap, not a low setting. Full map table, platform corrections,
and the red-teamed rung-5 recipe: `references/enforcement.md`.

## Session continuity: the boot chain

Continuity is files the harness auto-loads, chained by pointers (in real Glaze
the harness also ran task-boundary detection and wrote the history file — a
file-based replica puts that on the agent). **An artifact only persists if
it's reachable from the always-loaded file**; wiring it in is part of the step
that creates it:

- The boot file = whatever THIS harness actually auto-loads (the *harness
  file*; if it differs from the *convention file*, AGENTS.md, stub one at the
  other — verify empirically per `references/operations.md`). It carries: the
  skill-invocation rule (**just-in-time** — invoke each skill right before
  the work it governs, not all up front; when delegating, name skills in the
  subagent prompt instead: `references/runtime-discipline.md` §4), the inline
  enforcement map + the do-not-weaken rule and its sanctioned counterpart —
  the post-gate change protocol **inlined as its 6-step checklist**. NEVER
  write skill-relative paths (`references/…`) into project files: they are
  dead there. Plus pointers to the audit doc and memory files.
- Size test for always-on content: small, stable, load-bearing on every task.
  Anything that grows is a pointer.
- The audit doc is the resume artifact; every pass updates it in the same
  commit. Verify continuity with the **empirical orphan test**
  (`references/operations.md`), not self-assessment.

## Licensing

Replicate architecture and conventions; never copy component implementations
or doc text from proprietary references — write clean-room versions.
