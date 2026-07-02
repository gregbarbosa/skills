# `/thread` Harness Picker + Native Auto-Mode Mapping

**Date:** 2026-07-01
**Status:** Design approved → pending implementation plan
**Skill affected:** `~/.claude/skills/thread/SKILL.md` (+ new `harnesses.json`)

## Problem

`/thread` launches a new agent in a fresh herdr tab. Its launch step currently
hardcodes:

```
claude --permission-mode auto
```

…with a parenthetical that says "if the user asked for a specific binary (e.g.
`ds`), use that instead of `claude`." That parenthetical swaps the **binary**
but not the **flag** — so choosing `opencode` would hand it `--permission-mode
auto`, which is an invalid flag for opencode. There is also no way to *choose*
the harness at invocation time today; you get `claude` unless the agent happens
to notice you named another binary.

Greg uses several harnesses and wants to (a) pick which one `/thread` launches,
and (b) have each one launched with its **own native hands-off / auto-mode
flag**, since the flag differs per harness and drifts over time (opencode "just
got yolo mode").

## Goals

1. Pick the harness when invoking `/thread` — fast when you know it, guided when
   you don't.
2. Launch each harness with its exact native auto/yolo flag (no one-size-fits-all
   flag that's wrong for 2 of 5 harnesses).
3. Make the harness→launch mapping cheap to extend and fix without rewriting the
   skill.

## Non-goals

- Model selection (glm/ds bake the model into a shell function; opencode/pi use
  their default models). A per-harness `model` field is a trivial future schema
  extension, deliberately deferred.
- Replacing the rest of the thread flow (tab label, caller-pane callback,
  wait-for-prompt, send request + Enter) — unchanged.

## Verified per-harness auto-mode flags

Researched 2026-07-01 against installed binaries (`claude`, `opencode`, `pi`)
and the `glm`/`ds` zsh function definitions:

| harness | binary           | auto/yolo launch flag         | notes |
|---------|------------------|-------------------------------|-------|
| claude  | `claude`         | `--permission-mode auto`      | `auto` is a valid `--permission-mode` value (choices: `acceptEdits`, `auto`, `bypassPermissions`, `default`, `dontAsk`, `plan`). Full bypass also available via `--dangerously-skip-permissions`. |
| glm     | zsh **function** → `claude` | `--permission-mode auto` | Same `claude` binary; sets Z.ai/GLM env vars then calls `claude "$@"`. |
| ds      | zsh **function** → `claude` | `--permission-mode auto` | Same `claude` binary; sets DeepSeek env vars then calls `claude "$@"`. |
| opencode| `opencode`       | `--auto`                      | `--auto` = "auto-approve permissions that are not explicitly denied." **`yolo` is a config value, not a CLI flag.** |
| pi      | `pi`             | `--approve`                   | **No true bypass exists.** `--approve`/`-a` = "trust project-local files for this run." pi is permissive by default (read/bash/edit/write tools on) and gates via `--tools`/`--exclude-tools`; its model differs from Claude Code. `--approve` is the closest hands-off launch. |

## Design

### Decisions (from brainstorming)

- **Selection UX:** arg + fallback prompt. Type the harness when you know it
  (`/thread opencode <request>`); get a picker only when you omit it or type an
  unknown one.
- **Registry:** config-driven. The harness→launch mapping lives in
  `harnesses.json` co-located with the skill, read at launch time.

### File changes

1. **New** `~/.claude/skills/thread/harnesses.json` — the registry.
2. **Edit** `~/.claude/skills/thread/SKILL.md` — insert a harness-selection step
   before the current launch step, and rewrite the launch step to run
   `{command} {auto_flag}` from the chosen registry entry (replacing the
   hardcoded `claude --permission-mode auto`).

### Registry schema (`harnesses.json`)

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

Fields:

- `name` — token matched in the arg form and listed in the picker.
- `label` — human label shown in the picker.
- `command` — what is typed into the pane (for `glm`/`ds`, the function name;
  resolves in the pane's interactive shell).
- `auto_flag` — the harness's native hands-off flag. Empty string = launch with
  no auto flag.
- `default` — name of the harness used when the picker is skipped or declined.
- `prompt_on_missing` — `true` = show the picker when no harness is detected;
  `false` = silently use `default` (scriptable).

### Selection flow (new step inserted before the launch step)

1. Read `harnesses.json`. If missing or invalid JSON, fall back to the 5-entry
   inline default above and warn the user that the config was ignored.
2. Detect the harness from the user's message:
   - **Explicit form:** message starts with `--harness <name>` or `-h <name>` →
     use `<name>`, strip the flag + name from the request. (Escape hatch for
     requests that legitimately begin with a harness-named word.)
   - **Bare form:** first whitespace-delimited token equals a registry `name` →
     use it, strip that token from the request.
   - Otherwise: no harness detected.
3. Detected + valid → use it. Detected but unknown → warn, fall through to the
   picker.
4. Not detected → if `prompt_on_missing`, present a numbered text menu
   (`1. claude … 5. pi`; blank line = `default`) and read the choice. Numbered
   text menu chosen over AskUserQuestion because it has no option-count cap and
   stays terminal-native.

### Launch step (rewritten)

```
herdr pane run "<pane_id>" "<command> <auto_flag>"
```

Values come from the chosen registry entry. All surrounding steps (tab label,
caller-pane callback wiring, wait-for-`❯`, send request + Enter, final report)
are unchanged.

## Risks & open items (to verify at implementation, not now)

- **glm/ds are shell functions, not binaries.** They resolve only if the spawned
  pane's shell sources Greg's profile (where `glm`/`ds` are defined). `pane run`
  types into the pane's interactive shell, so this *should* work — but it is the
  #1 thing to verify live. Fallback if a function is not found: override the
  entry's `command` (e.g. `zsh -ic 'glm'`).
- **pi has no true bypass.** Documented above; `--approve` is the closest. If
  Greg later wants a stricter/safer pi launch, `auto_flag` is editable per-entry.
- **Model selection is out of scope** (see Non-goals).

## Implementation outline (detailed plan comes from the writing-plans step)

1. Create `harnesses.json` with the seed above.
2. Edit `SKILL.md`: add the registry-read + selection step; rewrite the launch
   step to use `{command} {auto_flag}`; keep the existing fallback note but
   reframe it around the registry.
3. Manual verification (live, in herdr): `/thread <harness> <request>` for each
   of claude/glm/ds/opencode/pi; confirm the correct auto flag lands and the
   harness actually starts in auto/yolo mode. Pay special attention to glm/ds
   (shell-function resolution).
