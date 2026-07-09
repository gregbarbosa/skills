# Runtime discipline: the muscles behind the skeleton

Read when: writing the pattern-table skill, the rules skills, orchestration,
or per-project memory. The static architecture (kit/docs/gate/tokens) makes
apps *consistent*; these runtime behaviors are where Glaze's apps got
*correct* and *cheap*. Derived from the real Glaze orchestrator prompt and
skill bodies (teardown: `docs/glaze-teardown.html` in the component-systems
repo, `~/src/component-systems` if checked out — otherwise skip it; do not
search).

## 1. Pattern-skill anatomy (the table is only a third of it)

Glaze's component-patterns skill is ~14KB; the gate + table are the smallest
part. A pattern skill must ALSO contain:

- **Never-hand-roll mapping** — a raw-element→component trigger table
  (`<button>`→Button, `<input>`→Input, `<ul>/<li>`→List, `<table>`→Table,
  raw `<div>` scroll→ScrollArea…). This is what makes the gate FIRE: the
  agent recognizes the banned move at the moment of typing it.
- **Selection decisions** — the branch points models get wrong, written as
  tests, not descriptions: "Dialog vs AlertDialog: is accidental Esc a safe
  no-op? then Dialog"; "SplitView vs PanelGroup: decided by column ROLES, not
  column count"; sugar API vs primitives boundaries; managed vs manual
  selection. Derive your platform's list from real mispredictions and add to
  it every time an agent picks wrong (lore-in-docs, applied to decisions).
- **Anti-default styling rules** — the model's web defaults are the enemy:
  no web-style cards (separate by structure, not decoration); role-based type
  variants (never raw `text-sm font-medium` when a `Text variant` exists);
  role-based radius tokens; `tabular-nums` for changing numbers; spacing
  hygiene (`gap-*` on the parent, `min-w-0`/`shrink-0` where flex bites).
- **Layout invariants** — per-platform hard rules ("every movable window has
  a Toolbar or drag-region"; "one `accent` button per screen"; z-index/sticky
  ladder).
- **A closing verification-gate checklist** — "the things agents actually
  botch", self-run before submitting UI work.

## 2. The validation loop (rules skill must include it)

Enforcement rigidity (the ladder) and *verify-what-you-built* are different
mechanisms; a system needs both. After EVERY change: type-check + lint. Build
via the canonical command only. Review delegated files BEFORE static checks.
Then graduated live inspection, cheapest first: DOM/tree snapshot → element
inspect → targeted evaluate → screenshot (expensive, last). With two explicit
dampers: don't inspect speculatively for trivial deterministic edits; DO
inspect before guessing on render-dependent fixes.

## 3. Delegation economics (the default is DON'T)

Glaze's orchestrator: "DEFAULT: no delegation. Sub-agents start cache-cold,
re-gather context, and often cost more than direct work." Delegate only when
a condition list is met (genuinely parallel workstreams, or a large isolated
single-layer task) — "if any condition is missing, do the work directly; do
not re-test this decision later." Handoff mechanics when you DO delegate:

- Shared contracts (e.g. IPC channel lists) passed **verbatim-identical** to
  both sides; spawn both agents in the SAME message.
- Handoff ≤ ~500 tokens; paths, never file contents; one task per subagent.
- Subagent output contract: ≤200 words, only Files / Decisions / Issues.
- The orchestrator owns integration and never hands work back to a subagent
  to avoid finishing it.
- Mixed-harness setups: if the delegate's harness can't load skills, paste
  the relevant reference section into the handoff (deliberately breaking the
  ≤500-token rule) — or don't delegate.
- Backend/native code is itself gated: only for file system, OS APIs,
  credentials, background work — "if unsure → frontend."

## 4. Skill invocation is just-in-time, not front-loaded

"Invoke the relevant skill BEFORE the work it governs" — not all skills up
front (bloats context, delays the first action, loads skills the task never
needs). Per-trigger granularity: window skill just before window code; docs
lookup fired in the background alongside unrelated work, blocking only at the
step that writes component code. When delegating, the orchestrator does NOT
invoke skills itself — it names them in the subagent's prompt.

## 5. Per-project memory: a schema, not a diary

`PROJECT-CONTEXT.md` is **overwrite-in-place**, not append: Overview (stable),
Current State (named subsections — components in play, channels/contracts,
settings), Recent History (newest-first, hard-capped ~5 entries). Update
after EVERY change, no matter how small — an un-updated context file is how
cold-session resume dies. `PROJECT-HISTORY.md` is the append-only log, read
on demand. Honest note: in real Glaze the harness wrote HISTORY and ran a
task-boundary classifier; a file-based replica makes the AGENT responsible
for both files — so the mandatory-update rule must live in the boot file, or
it won't happen.

## 6. Context-economy plumbing details

- **Docs-reader invariant: never trim props.** The API card condenses PROSE
  and examples, never the prop/variant table — when source reads are blocked,
  a silently-omitted prop has no recovery path. One call for ALL components
  needed; exact absolute paths only, no searching; a "Not found" protocol
  instead of hunting.
- **Guide line-number index.** A 50KB recipe guide is affordable only with a
  section index ("Critical Rules: lines 52–72 — use as Read offset; if
  shifted, grep the heading"). Regenerate the index when the guide changes.
- **Context-gather fork** for broad exploration (fork/cheap-model/read-only,
  "report, don't decide", ~400-word cap) so the main context never pays for
  discovery.

## 7. Theming lore is platform-compositing lore

Capture how the platform actually composites before authoring seeds. Glaze's
example: light-mode `--bg` rendered at 40% opacity over native window
material, so light seeds must be authored ~2.5× more saturated than intended
("push chroma until garish as a swatch"); dark seeds render as-authored. Also:
distinguish the theme accent from the OS accent the user controls (never
override the latter — chain them). Your platform will have its own version of
this; find it empirically with swatches before the token pass, and record it
in the theming artifact's doc.
