# Portable Skills Repo — Design

**Date:** 2026-07-01
**Status:** Approved (pending spec review)
**Owner:** Greg Barbosa (`gregbarbosa`)

## Goal

Give Greg a single, versioned, shareable home for his personal AI skills, starting with `/thread`. Anyone (including Greg across machines) can install a skill with one command:

```shell
npx skills add gregbarbosa/skills            # all skills
npx skills add gregbarbosa/skills -s thread  # just /thread
```

## Background

- `/thread` today is a **slash command** at `~/.claude/commands/thread.md`. It launches a new agent in a herdr tab (workspace lookup → `herdr tab create` → `pane run claude --permission-mode auto` → callback wiring to the caller pane).
- **`skills.sh`** is "npm for agent skills." A GitHub repo *is* the package; `npx skills add owner/repo` installs it. Discovery looks for `skills/<name>/SKILL.md`.
- **Command vs. skill:** the `skills` standard is `SKILL.md`-centric. Re-casting `/thread` as a `SKILL.md` is the price of admission for this pipeline. Functional impact is minimal:
  - `/thread <prompt>` still works (a skill named `thread` exposes a `/thread` surface).
  - Skills have no `$ARGUMENTS`; the user's message *is* the request (already how the body reads it).
  - A skill can auto-trigger; we prevent unwanted thread-spawns with a restrictive `description`.

## Scope

**In scope:** New `gregbarbosa/skills` repo; `/thread` re-cast as the first skill; documented add-a-skill workflow; local cutover from the old command.

**Out of scope (future):** migrating `herdr`, `xcodebuildmcp-cli`, and `gws-gmail*` skills into this repo. The structure supports it later; we don't do it now.

## Repo layout

Created locally at `~/src/skills` (matches existing convention: `~/src/quick-import`, `~/src/iMCP`), pushed to GitHub.

```
gregbarbosa/skills/
├── skills/
│   └── thread/
│       └── SKILL.md
├── README.md          # what's here + install + add-skill instructions
└── .gitignore
```

Flat `skills/<name>/SKILL.md` layout — the ecosystem standard. Future skills drop a new folder in.

## `thread/SKILL.md`

- **Frontmatter**
  - `name: thread`
  - `description:` phrased to block auto-trigger — *"Use ONLY when the user explicitly asks to launch or spawn a new agent thread in a herdr tab."*
- **Body:** the 10 steps from `commands/thread.md`, kept verbatim (workspace lookup, `herdr tab create`, `pane run`, caller-pane callback). One substitution: the trailing `User's request: $ARGUMENTS` becomes *"The user's request is the message they sent with this invocation."*

## Install mechanics

```shell
# Global (user-level), Claude Code, non-interactive — installs to ~/.claude/skills/thread/
npx skills add gregbarbosa/skills -s thread -g -a claude-code -y
```

Discovery container for Claude Code: `.claude/skills/` (project) or `~/.claude/skills/` (global via `-g`).

## Local cutover

Once the installed skill is verified working in a real herdr session, **delete the old** `~/.claude/commands/thread.md` to avoid a duplicate `/thread`. Deletion happens *only after* verification — never before.

## Add-a-new-skill workflow (in README)

```shell
cd ~/src/skills
npx skills init my-new-skill        # scaffolds skills/my-new-skill/SKILL.md
# edit, then:
git add . && git commit -m "Add my-new-skill" && git push
```

Pushed changes are live instantly — `npx skills add` pulls `main`.

## Verification

1. `npx skills add ~/src/skills --list` — confirms `thread` is discovered.
2. Install globally and confirm `/thread <prompt>` spawns a real herdr tab with the callback working.
3. Only after (2) succeeds, remove the old command.

## Decisions

| Decision | Choice | Note |
|---|---|---|
| Repo name | `gregbarbosa/skills` | Ecosystem convention; agent-agnostic |
| Visibility | **Public** | Required for `npx skills add` sharing; `/thread` has no secrets |
| Local path | `~/src/skills` | Matches `~/src/<repo>` convention |
| Distribution trunk | `main` | `npx skills add` pulls `main`; keep it shippable |

> Visibility and name are flagged defaults confirmed during brainstorming. Final go-ahead to **create the GitHub repo** happens at implementation, after this spec is reviewed.

## Branch policy

Brand-new repo: initial scaffold lands on `main` (no prior feature to branch off). For a skills registry, `main` is always the distributable trunk. Future skill additions may use short feature branches merged to `main` when ready — optional, not required.

## Risks / notes

- **Auto-trigger risk:** mitigated by a restrictive `description`. If `/thread` ever fires unprompted, tighten the description further.
- **Callback is best-effort** (already noted in the command body): if the spawned agent crashes before its final step, the ping won't fire. Behavior unchanged from today.
- **No secrets:** `/thread` references a "Vox" workspace name but contains nothing sensitive, so public publishing is safe.
