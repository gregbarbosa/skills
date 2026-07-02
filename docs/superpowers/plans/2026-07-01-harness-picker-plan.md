# `/thread` Harness Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `/thread` pick a harness (claude / glm / ds / opencode / pi) at invocation time and launch it with that harness's own native auto/yolo flag.

**Architecture:** A co-located JSON registry (`harnesses.json`) maps each harness to `{command, auto_flag}`. The skill reads it, detects the harness from the user's message (explicit flag, bare token, or a fallback picker), strips the harness token from the request, and launches `{command} {auto_flag}` instead of the hardcoded `claude --permission-mode auto`.

**Tech Stack:** herdr CLI, JSON (`jq` for validation), Markdown skill prose. No build system.

**Spec:** `~/.claude/skills/thread/specs/2026-07-01-harness-picker-design.md`

## Global Constraints

- **Live skill files, not a git repo.** `~/.claude` is not under version control (verified). There are **no commit steps** in this plan — edits are applied directly to the live files. The design doc (`specs/2026-07-01-harness-picker-design.md`) is the durable record. Do not `git init` `~/.claude`; that is Greg's call, not this plan's.
- **No unit-test framework exists for skill prose.** Verification uses three real surfaces instead: (1) a `jq` schema check for the registry, (2) a worked-example truth-table walk-through for the selection logic, (3) a live end-to-end run per harness inside herdr. Do not invent fake unit tests for Markdown.
- **Verified per-harness auto flags** (from the design; do not re-derive): claude / glm / ds → `--permission-mode auto`; opencode → `--auto`; pi → `--approve`. glm and ds are zsh **functions** that wrap `claude` (they forward `"$@"`, so the flag applies), not standalone binaries.
- **Preserve the existing thread flow.** Only the harness selection (new) and the launch command (rewrite) change. Tab-label derivation, caller-pane callback, wait-for-`❯`, send-request, and the final report stay — but their step numbers shift by +1 because selection becomes the new step 1, and two cross-references must be updated (see Task 2).

---

## File Structure

- **Create** `~/.claude/skills/thread/harnesses.json` — the registry. Data only; the skill reads it at launch. Single responsibility: map harness name → launch command + auto flag + picker label.
- **Modify** `~/.claude/skills/thread/SKILL.md` — insert a new "Select the harness" step as step 1, rewrite the launch step, and fix two step-number cross-references. The skill remains a flat numbered procedure (no code extraction; it is agent instructions).
- **Reference** `~/.claude/skills/thread/specs/2026-07-01-harness-picker-design.md` — already written; the source of truth for the why and the verified flag table.

---

## Task 1: Create the harness registry

**Files:**
- Create: `~/.claude/skills/thread/harnesses.json`

**Interfaces:**
- Produces: `harnesses.json` consumed by Task 2's skill prose. Schema: top-level object `{ default: string, prompt_on_missing: bool, harnesses: [{ name, label, command, auto_flag }] }`; `default` must equal one of the `name`s; names must be unique.

- [ ] **Step 1: Write the registry file**

Create `~/.claude/skills/thread/harnesses.json` with exactly this content:

```json
{
  "default": "claude",
  "prompt_on_missing": true,
  "harnesses": [
    { "name": "claude",   "label": "Claude (Anthropic)", "command": "claude",   "auto_flag": "--permission-mode auto" },
    { "name": "glm",      "label": "GLM (Z.ai)",         "command": "glm",      "auto_flag": "--permission-mode auto" },
    { "name": "ds",       "label": "DeepSeek",           "command": "ds",       "auto_flag": "--permission-mode auto" },
    { "name": "opencode", "label": "OpenCode",           "command": "opencode", "auto_flag": "--auto" },
    { "name": "pi",       "label": "Pi",                 "command": "pi",       "auto_flag": "--approve" }
  ]
}
```

- [ ] **Step 2: Validate the registry with `jq`**

Run this exact command (verified 2026-07-01 against valid + 3 invalid samples):

```bash
jq -e '
  . as $root |
  type == "object"
  and ($root | has("default")) and ($root.default | type == "string")
  and ($root | has("prompt_on_missing")) and ($root.prompt_on_missing | type == "boolean")
  and ($root | has("harnesses")) and ($root.harnesses | type == "array") and ($root.harnesses | length > 0)
  and ([$root.harnesses[].name] | unique | length == ($root.harnesses | length))
  and ([$root.harnesses[].name] | index($root.default) != null)
  and all($root.harnesses[];
          has("name") and has("label") and has("command") and has("auto_flag")
          and (.name|type=="string") and (.command|type=="string") and (.auto_flag|type=="string"))
' ~/.claude/skills/thread/harnesses.json && echo "registry OK"
```

Expected output: `true` then `registry OK`, exit code `0`.

- [ ] **Step 3: Confirm no commit needed**

`~/.claude` is not a git repo — there is nothing to commit. Note completion in the task report. Do not attempt `git add`.

---

## Task 2: Add harness selection + rewrite the launch step in SKILL.md

**Files:**
- Modify: `~/.claude/skills/thread/SKILL.md` (the numbered procedure; the `HERDR_ENV` guard paragraph at the top is unchanged)

**Interfaces:**
- Consumes: `harnesses.json` from Task 1 (schema above).
- Produces: updated skill prose where the agent (a) selects a harness + produces a cleaned `<request>`, (b) launches `{command} {auto_flag}`, (c) sends the cleaned `<request>`.

- [ ] **Step 1: Read the current SKILL.md**

Read `~/.claude/skills/thread/SKILL.md` in full so the Edit tool has exact match strings. Confirm it currently has the hardcoded launch step:

```
6. Launch Claude Code in that pane with auto-mode: `herdr pane run "<pane_id>" "claude --permission-mode auto"`. (If the user asked for a specific binary — e.g. `ds` — use that instead of `claude`.)
```

- [ ] **Step 2: Insert the new step 1 (Select the harness) before the current step 1**

Insert this as the first numbered step, and renumber every subsequent step by +1 (so the old step 1 "Derive a tab label" becomes step 2, etc.). The new step 1 text:

```markdown
1. **Select the harness and prepare `<request>`.** Read the registry at `~/.claude/skills/thread/harnesses.json`. If it is missing or not valid JSON, fall back to this inline default and tell the user the config file was ignored:

   ```json
   { "default": "claude", "prompt_on_missing": true, "harnesses": [
     { "name": "claude",   "label": "Claude (Anthropic)", "command": "claude",   "auto_flag": "--permission-mode auto" },
     { "name": "glm",      "label": "GLM (Z.ai)",         "command": "glm",      "auto_flag": "--permission-mode auto" },
     { "name": "ds",       "label": "DeepSeek",           "command": "ds",       "auto_flag": "--permission-mode auto" },
     { "name": "opencode", "label": "OpenCode",           "command": "opencode", "auto_flag": "--auto" },
     { "name": "pi",       "label": "Pi",                 "command": "pi",       "auto_flag": "--approve" }
   ] }
   ```

   Detect the harness from the user's message and produce `<request>` (the message with the harness selection removed):
   - **Explicit form:** if the message starts with `--harness <name>` or `-h <name>`, select `<name>` and strip the flag + name from the message to form `<request>`. (Escape hatch for tasks that legitimately begin with a harness-named word.)
   - **Bare token:** otherwise, if the first whitespace-delimited token equals a registry `name`, select it and drop that token to form `<request>`.
   - **None:** otherwise leave the whole message as `<request>`. If `prompt_on_missing` is true, present a numbered menu of the harnesses (`1. <label>` … `N. <label>`; a blank reply picks `default`) and use the choice. If `prompt_on_missing` is false, silently use `default`.

   If the selected name is not in the registry, warn the user and fall back to the picker (or `default`).

   Worked examples (registry = the 5 above):
   | user's message | harness | `<request>` |
   |---|---|---|
   | `opencode refactor the auth module` | opencode | `refactor the auth module` |
   | `--harness glm fix the flaky test` | glm | `fix the flaky test` |
   | `-h pi summarize this thread` | pi | `summarize this thread` |
   | `ds the data layer needs indexing` | ds | `the data layer needs indexing` |
   | `refactor the auth module` | (none → picker; blank = claude) | `refactor the auth module` |
   | `claude review src/api` | claude | `review src/api` |

   Call the selected entry's `command` value `<command>` and its `auto_flag` value `<auto_flag>`.
```

- [ ] **Step 3: Rewrite the launch step (old step 6, now step 7)**

Replace the hardcoded launch step:

```markdown
7. Launch the harness in that pane with its native auto flag: `herdr pane run "<pane_id>" "<command> <auto_flag>"`.
```

(This replaces the old `claude --permission-mode auto` line and its "specific binary" parenthetical — that behavior is now handled by the registry in step 1.)

- [ ] **Step 4: Update the two step-number cross-references**

The renumber shifts every step by +1, so two internal references must be fixed. Final numbering: 1 select, 2 label, 3 caller-pane, 4 workspace, 5 create-tab, 6 parse-pane, 7 launch, 8 wait, **9 send**, 10 enter, 11 report.
- The caller-pane step (old step 2 → now **step 3**) says "skip the callback wiring in **step 8**" → change to **step 9** (the send step, where the callback paragraph lives).
- The send step (old step 8 → now **step 9**) says "omit the callback paragraph if `<caller_pane>` was empty in **step 2**" → change to **step 3** (where `<caller_pane>` is now captured).

- [ ] **Step 5: Update the send-request step to use `<request>` (old step 8, now step 9)**

The send step currently sends `<the user's request>`. Change it to send the cleaned `<request>` produced in step 1. New text:

```markdown
9. Send `<request>` as the initial message, WITH a callback instruction appended so the agent pings the caller when done (omit the callback paragraph if `<caller_pane>` was empty in step 3):

   `herdr pane send-text "<pane_id>" "<request>\n\nWHEN YOU FINISH: notify the requesting agent by running these two commands so a message lands in their pane — herdr pane send-text \"<caller_pane>\" \"THREAD COMPLETE: <one-line summary of what you produced, incl. any file path>\"  then  herdr pane send-keys \"<caller_pane>\" Enter"`
```

Then confirm the caller-pane step's cross-reference (Step 4) points at this step 9.

- [ ] **Step 6: Verify with the truth-table walk-through**

With the edited SKILL.md open, mentally execute the skill for each row of the step-1 worked-examples table and confirm:
- The correct `<command>` and `<auto_flag>` are produced.
- `<request>` has the harness token stripped (so the spawned agent never receives the literal word `opencode`/`glm`/etc. as part of its task — except via the explicit `--harness`/`-h` forms which are also stripped).
- For the "None" row, the picker is presented (because `prompt_on_missing: true`).

Also confirm the final step count is 11 (was 10) and every step number referenced in prose exists.

- [ ] **Step 7: Confirm no commit needed**

Not a git repo — note completion. Do not `git add`.

---

## Task 3: Live end-to-end verification (all 5 harnesses)

**Files:** none modified (verification only). May modify `harnesses.json` only if the glm/ds fallback in Step 4 is triggered.

**Interfaces:** consumes the edited skill from Task 2.

This task runs inside herdr (`HERDR_ENV=1`). For each harness it spawns a real thread with a trivial, self-terminating task, then confirms the right command launched with the right auto flag and reached the agent prompt.

- [ ] **Step 1: Verify claude (baseline)**

From M's pane, invoke: `/thread claude reply with the single word OK, then stop`.

Expected: a new tab is created; the launched command is `claude --permission-mode auto`; the pane reaches the `❯`/agent prompt; the agent replies "OK". Confirm via `herdr pane read "<pane_id>" --source recent --lines 20`.

- [ ] **Step 2: Verify opencode**

Invoke: `/thread opencode reply with the single word OK, then stop`.

Expected: launched command is `opencode --auto` (NOT `--permission-mode auto`). Confirm the `--auto` flag appears in the pane and opencode reaches its prompt. Close the tab when done: `herdr tab close "<tab_id>"`.

- [ ] **Step 3: Verify pi**

Invoke: `/thread pi reply with the single word OK, then stop`.

Expected: launched command is `pi --approve`. Confirm `--approve` appears and pi reaches its prompt. Note: pi has no true bypass; `--approve` is the hands-off launch. Close the tab.

- [ ] **Step 4: Verify glm and ds (shell-function resolution — the high-risk case)**

Invoke each in turn: `/thread glm reply OK then stop` and `/thread ds reply OK then stop`.

For each, confirm the pane does NOT show `command not found` or `zsh: command not found: glm/ds` — i.e. the pane's interactive shell resolved the zsh **function**. Confirm the launched line is `glm --permission-mode auto` / `ds --permission-mode auto` and the agent reaches its prompt showing the GLM / DeepSeek model (not Anthropic).

**If a function is NOT found** (pane shell did not source the profile): edit `harnesses.json` for that entry, changing `command` to `zsh -ic 'glm'` (or `zsh -ic 'ds'`), re-validate with the Task 1 `jq` command, and re-run this step. Record which form was required.

- [ ] **Step 5: Verify the fallback picker**

Invoke: `/thread summarize the design doc` (no harness token, and "summarize" is not a harness name).

Expected: the agent presents the numbered harness menu and waits. Pick `2` (glm) and confirm the thread launches with glm. Then confirm the spawned agent's task is `summarize the design doc` (the harness token was not part of the request — here there was none, but confirm no leading bogus token leaked).

- [ ] **Step 6: Verify the explicit escape hatch**

Invoke: `/thread --harness opencode ds the directory structure` (task literally starts with "ds").

Expected: harness = opencode (from `--harness`), and `<request>` = `ds the directory structure` (the word "ds" stays in the request because the explicit form was used, not the bare token). Confirm the spawned opencode agent receives the full `ds the directory structure` task.

- [ ] **Step 7: Record results + clean up**

Close all verification tabs (`herdr tab close <id>`). Write a one-line-per-harness pass/fail summary into the task report, noting the glm/ds resolution form that worked and any deviation.

---

## Self-Review (run after writing, before handoff)

**1. Spec coverage:**
- Pick harness at invocation (arg + fallback prompt) → Task 2 step 1-2 (selection), Task 3 steps 5-6 (picker + escape hatch). ✓
- Each harness launched with its native flag → Task 2 step 3 (launch rewrite), Task 3 steps 1-4 (live check per harness). ✓
- Mapping cheap to extend/fix → Task 1 (data file, one-line edit). ✓
- glm/ds shell-function risk → Task 3 step 4 with documented fallback. ✓
- pi no-true-bypass noted → Global Constraints + Task 3 step 3. ✓
- Model selection out of scope → Global Constraints. ✓

**2. Placeholder scan:** No TBD/TODO. Every code/config step shows exact content. The two cross-reference updates in Task 2 steps 4-5 are specified by their old → new text; the implementer reads SKILL.md first (Task 2 step 1) to get exact match strings, which is a real instruction, not a placeholder.

**3. Consistency:** `<command>`/`<auto_flag>`/`<request>` are defined in Task 2 step 1 and used identically in steps 3 and 5 and verified in Task 3. `jq` check in Task 1 step 2 was executed and verified to pass on the seed and reject 3 invalid variants. Step numbering: final skill = 11 steps (selection inserted as step 1); cross-refs updated to match.

No gaps. Plan is ready.
