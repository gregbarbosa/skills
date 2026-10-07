---
name: backlog
description: Use ONLY when the user explicitly runs /backlog or asks to move the current pane/tab into the Backlog herdr workspace. Moves the current pane into the workspace labeled "Backlog", preserving the original tab's name. Requires running inside herdr.
---

Before using this skill, check that `HERDR_ENV=1`. If it is not set to `1`, tell the user you are not running inside a herdr-managed pane and stop. Do not attempt the steps below from outside herdr.

When invoked, execute these steps immediately without asking for confirmation:

1. Get your own pane id and tab id LIVE (do not trust a stale env var, it can go stale after a pane move): `herdr pane current`. Note `result.pane.pane_id` and `result.pane.tab_id`.

2. Get the name to preserve: `herdr tab get <tab_id>`. Use `result.tab.label` as the name to carry over. If a tab somehow has no `label` field, fall back to `terminal_title_stripped` from step 1's `pane current` output.

3. Find the target workspace: `herdr workspace list`. Find the workspace whose `label` contains "Backlog" (case-insensitive; ignore any emoji prefix like "⚪ "). If zero or more than one workspace matches, tell the user the workspace couldn't be resolved unambiguously and stop rather than guessing.

4. Move the pane into a new tab in that workspace, passing the preserved name as the tab label:
   `herdr pane move <pane_id> --new-tab --workspace <target_workspace_id> --label "<preserved_name>" --no-focus`
   Default to `--no-focus` (keeps the user's current view in place) unless they've asked to jump to the moved pane, in which case use `--focus` instead.

5. Confirm to the user in one line: which workspace the pane moved to and that the tab kept its original name.

## Common mistakes

- Using `--tab-label` — that flag only exists on the `--new-workspace` form of `pane move` (creating a brand-new workspace). Moving into an *existing* workspace with `--new-tab` takes the name via `--label` instead.
- Matching the target workspace by number or emoji instead of the text label substring — workspace numbers shift as workspaces are added or closed.
- Reading `terminal_id` where `pane_id` is meant — `pane move` takes the pane_id (e.g. `w4:p3N`), not the terminal_id (e.g. `term_...`).

## Verified

Tested live 2026-07-31 against herdr: created a disposable tab labeled "backlog-skill-test" in the current workspace, ran `herdr pane move <id> --new-tab --workspace <backlog-workspace-id> --label "backlog-skill-test" --no-focus`, confirmed the resulting tab in the Backlog workspace kept the exact label, then closed the test tab.

## Related (planned)

Sibling commands `/in-progress` and `/blocked` will follow the same five steps against workspaces labeled "In Progress" and "Blocked" respectively — not yet built.
