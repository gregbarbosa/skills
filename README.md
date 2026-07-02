# Greg Barbosa's Agent Skills

Personal, reusable [Agent Skills](https://skills.sh) for AI coding agents — Claude Code, Codex, Cursor, and 70+ others.

## Skills

| Skill | Description |
| --- | --- |
| `thread` | Launch a new agent thread in a herdr tab, with a fire-and-forget callback to the caller's pane. Requires herdr. |

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

Pushed changes are live immediately — `npx skills add` pulls `main`.

## Layout

```
skills/
  <name>/SKILL.md
```

Each skill is one folder containing a `SKILL.md`. The `skills` CLI discovers them automatically.
