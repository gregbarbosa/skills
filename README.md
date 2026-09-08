# Greg Barbosa's Agent Skills

Personal, reusable [Agent Skills](https://skills.sh) for AI coding agents: Claude Code, Codex, Cursor, and 70+ others.

## Skills

| Skill | Description |
| --- | --- |
| `field-agent` | Dispatch work to one field agent in a herdr tab or worktree. Names the agent, records it in the field ledger, arms a watch loop, and triages each report. Requires herdr >= 0.9.0. |
| `field-handler` | This session becomes the handler: it opens a room of parallel field agents on one theme and steers them itself. Surfaces on its own when work gets complex; never spawns without agreement. Requires herdr >= 0.9.0. |
| `field-audit` | Read each field agent's result, verify it, then close only the panes that are provably finished. Requires herdr >= 0.9.0. |
| `herdr` | The herdr command surface: workspaces, tabs, panes, agents, and agent status. The three `field-*` skills assume this one. |
| `component-system-builder` | Stand up a closed-world component + agent-rules system for a platform (Electron, Astro, SwiftUI, …), or retrofit one onto an existing project through an audited, pass-by-pass loop. Makes AI-generated apps consistent by removing choices. |

### `field-agent` harness picker

`/field-agent` lets you pick which agent harness runs the new tab. Name it explicitly, or get a numbered menu:

```shell
/field-agent opencode refactor the auth module   # explicit harness
/field-agent --harness glm fix the flaky test    # explicit, unambiguous form
/field-agent refactor the auth module            # no harness → numbered picker (blank = default)
```

The registry is `skills/field-agent/harnesses.json` (`claude`, `glm`, `ds`, `opencode`, `pi` by default). Edit it to add or change harnesses; if the file is missing or invalid, the skill falls back to an inline default. Each harness launches in its own native auto/yolo flag (`--permission-mode auto`, `--auto`, `--approve`, …).

### The field: one handler, many agents

**The four `field-*` and `herdr` skills are one suite. Install them together:**

```shell
npx skills add gregbarbosa/skills -s '*' -g -y
```

That installs into `~/.agents/skills` and links every detected agent to it.

If you have PromptScript installed, expect a line like
`✗ herdr → PromptScript does not support global skill installation`. **It is
harmless.** PromptScript has no global scope; every other agent still installs.
Check with `npx skills list -g`. To avoid the message, name your agents instead,
repeating `-a` because a comma list is rejected:

```shell
npx skills add gregbarbosa/skills -s '*' -g -y \
  -a claude-code -a pi -a opencode -a hermes-agent -a gemini-cli
```

The `skills` packaging format has no group or dependency concept, so the grouping is a convention the skills state and check themselves: `field-handler` and `field-audit` look for `field-agent`'s directory on startup, and stop with this command if it is missing.


The vocabulary is borrowed from an intelligence service. **You** are the handler. Each agent you start is a **field agent**.

`field-agent` dispatches one. It names the agent, records it in the ledger (`~/.claude/field/ledger.json`), and arms a watch loop that reports every state change. `field-handler` dispatches several on one shared theme and keeps this session steering them. `field-audit` sweeps up: it reads each result, verifies the work, and closes only the panes that are acknowledged and clean. `herdr` documents the command surface all three use.

The ledger tool `field.py` has exactly one copy, in `skills/field-agent/`. `field-handler` and `field-audit` call it there. Do not copy it into another skill folder; a second copy goes stale the moment the first one changes.

### `field-handler`: run a room of field agents

`/field-handler` is usually not typed. It surfaces on its own when work is growing complex or splitting into independent strands, offers to open a room, and agrees the scope with you first. On agreement it opens a herdr workspace with one field agent per project. **This session becomes the handler** — it watches, steers and reports, rather than delegating to a second pane. Their reports arrive as turns here, so the room shares this conversation.

You can also invoke it directly:

```shell
/field-handler get the zoho lead projects aligned on one shared match key
```

Config is `skills/field-handler/handler.json` (agent model, and `layout_threshold`: panes side-by-side at or below the threshold, one tab per agent above it). Per-agent harness overrides reuse `field-agent`'s `harnesses.json`.

**Requires herdr >= 0.9.0.** The skill checks `HERDR_ENV=1` and stops cleanly if you are not inside a herdr-managed pane.

**Optional hardening (for yourself only):** to make the proactive offer fire more reliably, add one line to your global `~/.claude/CLAUDE.md`:

> When work is growing complex or splitting into independent strands across projects, proactively offer to open a room with the `field-handler` skill: name the strands, agree scope with me, then spin them up. Never spawn without that conversation.

This is not required for the skill to work and does not travel with the package.

### `component-system-builder`: consistency by removing choices

The premise is that an agent produces consistent, polished UI when the platform gives it fewer choices, not when the model is smarter. The skill builds six artifacts — a component kit with docs beside source, seed-variable theming, a pattern-table gate, rules skills plus a tiny always-on constraints file, context-economy plumbing, and a scaffold — and places each rule as high on an enforcement ladder as the platform allows (prose → checklists → the gate → closed type surfaces → lint/CI → physically blocked).

Two modes. Green-field starts from a platform scaffold and builds outward. Retrofit runs an audit loop over an existing project, one merge-able commit per pass: inventory, tokens, componentize, build the gate, then mechanical enforcement. Each pass writes its state into `docs/system-audit.md`, so a cold session can resume from it.

```shell
/component-system-builder retrofit a component system onto this Astro site
```

Three reference files (`references/operations.md`, `references/enforcement.md`, `references/runtime-discipline.md`) load on demand rather than up front.

## Install

Requires Node.js (for `npx`).

```shell
# Install all skills, globally, for Claude Code
npx skills add gregbarbosa/skills -g -a claude-code -y

# Install just one skill
npx skills add gregbarbosa/skills -s field-agent -g -a claude-code -y
```

Drop the `-g` flag to install into the current project (`.claude/skills/`) instead of your user directory.

## Add or modify a skill

```shell
git clone https://github.com/gregbarbosa/skills.git
cd skills
npx skills init my-new-skill        # scaffolds skills/my-new-skill/SKILL.md
# edit skills/my-new-skill/SKILL.md, then:
git add . && git commit -m "Add my-new-skill" && git push
```

Pushed changes are live immediately; `npx skills add` pulls `main`.

## Layout

```
skills/
  <name>/SKILL.md
  <name>/references/*.md      # optional, loaded on demand
  <name>/<config>.json        # optional
```

Each skill is one folder containing a `SKILL.md`. The `skills` CLI discovers them automatically, and sibling files and subdirectories install alongside it.
