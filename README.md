# Greg Barbosa's Agent Skills

Personal, reusable [Agent Skills](https://skills.sh) for AI coding agents: Claude Code, Codex, Cursor, and 70+ others.

## Skills

| Skill | Description |
| --- | --- |
| `thread` | Launch a new agent thread in a herdr tab via a chosen harness, with a fire-and-forget callback to the caller's pane. Requires herdr. |
| `advise` | Offer to fan work out across parallel herdr sessions, agree scope, then spin up one Sonnet worker per project plus a Fable advisor that watches and nudges them. Surfaces on its own when work gets complex; never spawns without agreement. Requires herdr. |

### `thread` harness picker

`/thread` lets you pick which agent harness runs the new tab. Name it explicitly, or get a numbered menu:

```shell
/thread opencode refactor the auth module   # explicit harness
/thread --harness glm fix the flaky test    # explicit, unambiguous form
/thread refactor the auth module            # no harness → numbered picker (blank = default)
```

The registry is `skills/thread/harnesses.json` (`claude`, `glm`, `ds`, `opencode`, `pi` by default). Edit it to add or change harnesses; if the file is missing or invalid, the skill falls back to an inline default. Each harness launches in its own native auto/yolo flag (`--permission-mode auto`, `--auto`, `--approve`, …).

### `advise`: orchestrate parallel sessions

`/advise` is usually not typed. It surfaces on its own when work is growing complex or splitting into independent strands, offers to spin up parallel sessions, and agrees scope with you first. On agreement it opens a herdr workspace with one Sonnet worker per project plus a Fable advisor pane that watches and nudges them. You can jump into any pane at any time.

You can also invoke it directly:

```shell
/advise get the zoho lead projects aligned on one shared match key
```

Config is `skills/advise/advise.json` (worker model, advisor model, and `layout_threshold`: panes side-by-side at or below the threshold, one tab per worker above it). Per-worker harness overrides reuse `thread`'s `harnesses.json`.

**Requires herdr.** The skill checks `HERDR_ENV=1` and stops cleanly if you are not inside a herdr-managed pane.

**Optional hardening (for yourself only):** to make the proactive offer fire more reliably, add one line to your global `~/.claude/CLAUDE.md`:

> When work is growing complex or splitting into independent strands across projects, proactively offer to orchestrate parallel sessions with the `advise` skill: name the strands, agree scope with me, then spin them up. Never spawn without that conversation.

This is not required for the skill to work and does not travel with the package.

## Install

Requires Node.js (for `npx`).

```shell
# Install all skills, globally, for Claude Code
npx skills add gregbarbosa/skills -g -a claude-code -y

# Install just one skill
npx skills add gregbarbosa/skills -s thread -g -a claude-code -y
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
```

Each skill is one folder containing a `SKILL.md`. The `skills` CLI discovers them automatically.
