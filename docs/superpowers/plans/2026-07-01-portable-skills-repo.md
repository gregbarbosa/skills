# Portable Skills Repo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `gregbarbosa/skills` as a shareable home for personal AI skills, with `/thread` (re-cast from a slash command to a `SKILL.md`) as the first entry, installable via `npx skills add gregbarbosa/skills`.

**Architecture:** Flat `skills/<name>/SKILL.md` layout — the `skills.sh` ecosystem standard. The repo *is* the package; `npx skills add owner/repo` clones and symlinks/copies each `SKILL.md` into the target agent's skills directory. Greg's local working copy lives at `~/src/skills`; `main` is the distributable trunk.

**Tech Stack:** Markdown (`SKILL.md`), Git, GitHub (`gh` CLI), the `skills` CLI (`npx skills`), herdr (for behavioral verification of `/thread`).

## Verification Approach (read first)

There is **no automated test suite** — this is a skills/docs repo. Each task's "test cycle" is a concrete verification command (a `npx skills`/`ls`/`cat` invocation) with expected output, culminating in one manual herdr run for `/thread`. Treat those steps as the tests: run them, observe the expected output, and only commit when they pass.

## Global Constraints

- Repo name `gregbarbosa/skills`, **public**, local path `~/src/skills`.
- Distribution trunk is `main` — keep it shippable; `npx skills add` pulls `main`.
- Skill discovery path: `skills/<name>/SKILL.md`.
- The `thread` skill's `description` MUST block auto-triggering (only fire on explicit user request).
- Preserve the herdr command steps from `~/.claude/commands/thread.md` verbatim, **except** one fix: the original step 2 says "skip the callback wiring in step 7" — the callback wiring is actually in step 8, so correct that cross-reference to "step 8".
- No secrets. `/thread` references a "Vox" workspace name but nothing sensitive.
- Replace `$ARGUMENTS` usage: skills have no `$ARGUMENTS`; the user's message *is* the request.

---

### Task 1: Repo foundation (`.gitignore` + README skeleton)

The repo already exists (`git init -b main` done, spec committed at root commit `073f4c8`). This task adds the base project files.

**Files:**
- Create: `~/src/skills/.gitignore`
- Create: `~/src/skills/README.md`

**Interfaces:**
- Produces: a `README.md` skeleton that Task 3 fleshes out; a `.gitignore` that keeps OS cruft out of every later commit.

- [ ] **Step 1: Create `.gitignore`**

Create `~/src/skills/.gitignore` with:

```gitignore
# macOS
.DS_Store

# Node (npx skills may drop these in some flows)
node_modules/

# Editor
.vscode/
.idea/
```

- [ ] **Step 2: Create README skeleton**

Create `~/src/skills/README.md` with:

```markdown
# Greg Barbosa's Agent Skills

Personal, reusable [Agent Skills](https://skills.sh) for AI coding agents (Claude Code, Codex, Cursor, and 70+ others).

## Skills

| Skill | Description |
| --- | --- |
| `thread` | Launch a new agent thread in a herdr tab with a fire-and-forget callback. |

## Install

<!-- Task 3 fills this in. -->
```

- [ ] **Step 3: Verify files exist and are ignored-free**

Run: `ls -la ~/src/skills && cat ~/src/skills/README.md`
Expected: `.gitignore` and `README.md` listed; README shows the title, skills table with `thread`, and an Install stub.

- [ ] **Step 4: Commit**

```bash
git -C ~/src/skills add .gitignore README.md
git -C ~/src/skills commit -m "Add .gitignore and README skeleton"
```

---

### Task 2: The `thread` skill (`skills/thread/SKILL.md`)

The core deliverable: `/thread` re-cast as a `SKILL.md`, ported from `~/.claude/commands/thread.md`.

**Files:**
- Create: `~/src/skills/skills/thread/SKILL.md`

**Interfaces:**
- Consumes: the command body at `~/.claude/commands/thread.md` (source of truth for the 10 steps).
- Produces: `skills/thread/SKILL.md` — discoverable by `npx skills add` and installable into `~/.claude/skills/thread/`.

- [ ] **Step 1: Create the skill directory**

Run: `mkdir -p ~/src/skills/skills/thread`
Expected: no output; directory created.

- [ ] **Step 2: Write `skills/thread/SKILL.md`**

Create `~/src/skills/skills/thread/SKILL.md` with exactly:

````markdown
---
name: thread
description: Use ONLY when the user explicitly asks to launch or spawn a new agent thread in a herdr tab. Spawns a new Claude Code (or a user-specified binary) in a fresh herdr tab, runs the user's request inside it, and wires a fire-and-forget callback so the spawned agent pings the caller's pane when it finishes. Requires running inside herdr.
---

Before using this skill, check that `HERDR_ENV=1`. If it is not set to `1`, tell the user you are not running inside a herdr-managed pane and stop. Do not attempt the steps below from outside herdr.

When invoked, execute these steps immediately without asking for confirmation:

1. Derive a short, descriptive tab label from the user's request (max 30 chars, kebab-case or title case).
2. Capture YOUR OWN pane id so the spawned agent can call back: `echo "$HERDR_PANE_ID"` (e.g. `w653…:p9`). Call this `<caller_pane>`. If it's empty (not running inside herdr — should not happen given the check above, but guard anyway), skip the callback wiring in step 8 and just note that to the user.
3. Find the current workspace ID from `herdr workspace list` (the focused one, or workspace 3 if there's a "Vox" workspace).
4. Create a new herdr tab with that label: `herdr tab create --workspace <N> --label "<label>"`
5. Parse the root pane ID from the JSON response (field: `result.root_pane.pane_id`). Call this `<pane_id>`. Also note the new pane's `cwd` from the response — if it differs from the directory the task concerns, pass ABSOLUTE paths in the request so the agent can find files regardless of its working directory.
6. Launch Claude Code in that pane with auto-mode: `herdr pane run "<pane_id>" "claude --permission-mode auto"`. (If the user asked for a specific binary — e.g. `ds` — use that instead of `claude`.)
7. Wait for the prompt: `herdr wait output "<pane_id>" --match "❯" --regex --timeout 60000`
8. Send the full user request as the initial message, WITH a callback instruction appended so the agent pings the caller when done (omit the callback paragraph if `<caller_pane>` was empty in step 2):

   `herdr pane send-text "<pane_id>" "<the user's request>\n\nWHEN YOU FINISH: notify the requesting agent by running these two commands so a message lands in their pane — herdr pane send-text \"<caller_pane>\" \"THREAD COMPLETE: <one-line summary of what you produced, incl. any file path>\"  then  herdr pane send-keys \"<caller_pane>\" Enter"`
9. Press Enter: `herdr pane send-keys "<pane_id>" Enter`
10. Report the tab label, pane ID, the caller pane the agent will call back to, and confirm the agent is running. Note that the callback is fire-and-forget (best-effort): if the spawned agent crashes before its final step the ping won't fire, so for critical work keep a fallback (ask, or check for the expected output file).

The user's request is the message they sent with this invocation.
````

- [ ] **Step 3: Verify frontmatter + body**

Run:
```bash
head -4 ~/src/skills/skills/thread/SKILL.md
grep -c "description:" ~/src/skills/skills/thread/SKILL.md
grep -n 'step 8' ~/src/skills/skills/thread/SKILL.md
grep -c '$ARGUMENTS' ~/src/skills/skills/thread/SKILL.md
```
Expected:
- `head` shows `name: thread` and a `description:` line beginning "Use ONLY when…".
- `grep -c "description:"` → `1`.
- `grep -n 'step 8'` → a hit in step 2 (the corrected cross-reference). **No** hit referencing "step 7" for callback wiring.
- `grep -c '$ARGUMENTS'` → `0` (single-quoted, so grep searches for the literal token, which must be gone).

- [ ] **Step 4: Commit**

```bash
git -C ~/src/skills add skills/thread/SKILL.md
git -C ~/src/skills commit -m "Add thread skill (ported from commands/thread.md)"
```

---

### Task 3: Complete the README (install + add-skill workflow)

**Files:**
- Modify: `~/src/skills/README.md` (replace the Install stub; add a development section)

**Interfaces:**
- Produces: the public-facing instructions that make the repo self-documenting.

- [ ] **Step 1: Rewrite `README.md` in full**

Overwrite `~/src/skills/README.md` with:

````markdown
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
````

- [ ] **Step 2: Verify README renders sensibly**

Run: `cat ~/src/skills/README.md`
Expected: title, skills table with `thread`, Install section with the two `npx skills add` commands, an "Add or modify a skill" section, and a Layout section. No `<!-- Task 3 ... -->` stub remains.

- [ ] **Step 3: Commit**

```bash
git -C ~/src/skills add README.md
git -C ~/src/skills commit -m "Document install and add-skill workflow in README"
```

---

### Task 4: Verify skill discovery + local install

Confirm the `skills` CLI sees `thread`, then install it globally on Greg's machine. **No repo commit** unless a fix is needed — this is verification.

**Files:** none modified (verification only). Possibly `~/src/skills/README.md` if real CLI output contradicts the documented commands (then amend Task 3's commit).

**Interfaces:**
- Produces: `~/.claude/skills/thread/` installed and visible to Claude Code, ready for the behavioral test in Task 5.

- [ ] **Step 1: Confirm discovery from the local repo**

Run: `npx -y skills add ~/src/skills --list`
Expected: output listing `thread` as an available skill (and nothing else). If `thread` does not appear, the discovery path is wrong — confirm the file is at `~/src/skills/skills/thread/SKILL.md` with valid frontmatter before proceeding.

- [ ] **Step 2: Install globally for Claude Code**

Run: `npx -y skills add ~/src/skills -g -a claude-code -s thread -y`
Expected: a success message stating `thread` was installed for `claude-code` in the global/user directory. The CLI **symlinks by default**; `~/.claude/skills/thread` will point at `~/src/skills/skills/thread` (live edits to the repo are immediately reflected). If you'd prefer a copy instead, re-run with `--copy`.

- [ ] **Step 3: Confirm the install landed**

Run:
```bash
ls -la ~/.claude/skills/thread/
npx -y skills list
```
Expected:
- `ls` shows `SKILL.md` (or a symlink to it).
- `skills list` shows `thread` installed for claude-code.

- [ ] **Step 4: (Only if real output differed) amend docs**

If the actual `npx skills` flags or install path differed from what Task 3 documented, fix `README.md` to match reality and `git -C ~/src/skills commit --amend --no-edit` (or a follow-up fix commit). Otherwise, no commit.

---

### Task 5: Behavioral verification + reversible cutover

Run `/thread` for real inside herdr. Because the old command `~/.claude/commands/thread.md` would collide with the new skill for the `/thread` name, do a **reversible** cutover: set the old command aside first, test the skill, then discard or restore the backup.

**Files:**
- Modify (rename): `~/.claude/commands/thread.md` → `~/.claude/commands/thread.md.bak`, then delete the `.bak` on success.

**Interfaces:**
- Produces: confirmation that the `thread` skill spawns a herdr tab and the callback reaches the caller pane; the old command removed.

- [ ] **Step 1: Confirm you're in a herdr session**

Run: `echo "$HERDR_ENV"` and `echo "$HERDR_PANE_ID"`
Expected: `HERDR_ENV=1` and a non-empty pane id. If not running inside herdr, **stop** and run this task from a herdr-managed pane.

- [ ] **Step 2: Set the old command aside (reversible)**

Run: `mv ~/.claude/commands/thread.md ~/.claude/commands/thread.md.bak`
Expected: no output. Now only the `thread` *skill* answers `/thread`.

- [ ] **Step 3: Run `/thread` with a small, safe prompt**

In the herdr Claude Code pane, invoke:
```
/thread echo "hello from the spawned thread" to a temp file at /tmp/thread-skill-test.txt
```
Expected behavior:
- A new herdr tab is created with a short label derived from the request.
- Claude Code launches in that tab in auto-permission mode.
- The spawned agent writes `/tmp/thread-skill-test.txt`.
- When it finishes, a `THREAD COMPLETE: …` message lands back in the caller pane (best-effort).

- [ ] **Step 4: Verify the spawned side produced output**

Run: `cat /tmp/thread-skill-test.txt`
Expected: the file exists with `hello from the spawned thread`.

- [ ] **Step 5: On success, remove the old command backup**

Run: `rm ~/.claude/commands/thread.md.bak && rm /tmp/thread-skill-test.txt`
Expected: no output. Cutover complete — the `thread` skill is now the sole `/thread`.

> **On failure:** restore the old command with `mv ~/.claude/commands/thread.md.bak ~/.claude/commands/thread.md`, then debug `skills/thread/SKILL.md` (re-commit any fix) and repeat from Step 2. Do not publish (Task 6) until this passes.

---

### Task 6: Publish to GitHub

**This is the outward-facing step.** The skill is verified locally (Task 5) before this runs. The repo goes public as `gregbarbosa/skills`.

**Files:** none in the repo (creates the remote + pushes).

**Interfaces:**
- Produces: a public GitHub repo `gregbarbosa/skills` whose `main` branch is installable via `npx skills add gregbarbosa/skills`.

- [ ] **Step 1: Create the public repo and push**

Run:
```bash
gh repo create gregbarbosa/skills --public --source="$HOME/src/skills" --remote=origin --push \
  --description "Greg Barbosa's personal agent skills — installable via npx skills add gregbarbosa/skills"
```
Expected: gh creates `gregbarbosa/skills`, adds `origin`, and pushes `main`. Ends with the repo URL.

- [ ] **Step 2: Verify the remote install path works**

Run: `npx -y skills add gregbarbosa/skills --list`
Expected: `thread` listed, resolved from the remote repo (not the local path). This proves anyone else can install it the same way.

- [ ] **Step 3: Confirm repo visibility + contents**

Run: `gh repo view gregbarbosa/skills --json visibility,url,defaultBranchRef -q '"\(.visibility) \(.url) \(.defaultBranchRef.name)"'`
Expected: `PUBLIC https://github.com/gregbarbosa/skills main`.

- [ ] **Step 4: Note skills.sh indexing (no action required)**

skills.sh indexes public GitHub repos over time; `gregbarbosa/skills` will appear on the directory automatically. No publish command is needed — the GitHub repo *is* the package. Optionally check `https://skills.sh/gregbarbosa/skills` later.

---

## Done criteria

- `~/src/skills` has `skills/thread/SKILL.md`, `README.md`, `.gitignore`, all committed on `main`.
- `npx skills add gregbarbosa/skills --list` (remote) lists `thread`.
- On Greg's machine, `/thread` runs from the skill (old command removed) and spawns a working herdr tab with callback.
- `gregbarbosa/skills` is public on GitHub and pushed.
