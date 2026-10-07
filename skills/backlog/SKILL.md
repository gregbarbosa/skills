---
name: backlog
description: Move the current herdr pane into a new tab in the workspace labeled "Backlog", keeping the original tab's name. Use when the user runs /backlog or asks to send this pane or tab to the backlog. Requires a herdr pane (HERDR_ENV=1).
---

Check that `HERDR_ENV=1` first. If it is not, tell the user this session is not in a herdr-managed pane and stop, because every step below talks to the herdr server.

Run the steps straight through; the user asked for the move, so it needs no confirmation.

1. Read your own pane and tab ids live with `herdr pane current`, noting `result.pane.pane_id` and `result.pane.tab_id`. An id from an environment variable can be stale after an earlier pane move.

2. Read the name to carry over with `herdr tab get <tab_id>`, taking `result.tab.label`. If the tab has no `label`, use `terminal_title_stripped` from step 1's output.

3. Find the target with `herdr workspace list`: the one workspace whose `label` contains "Backlog", case-insensitive, ignoring any emoji prefix. Match on the label text, since workspace numbers shift as workspaces open and close. If zero or several match, tell the user the target is ambiguous and stop.

4. Move the pane into a new tab there, passing the preserved name:
   `herdr pane move <pane_id> --new-tab --workspace <target_workspace_id> --label "<preserved_name>" --no-focus`
   `--no-focus` keeps the user's view where it is; use `--focus` only when they asked to follow the pane.

5. Confirm in one line: the workspace the pane moved to, and that the tab kept its name.

## Gotchas

- Moving into an existing workspace with `--new-tab` takes the name as `--label`. `--tab-label` belongs to the `--new-workspace` form only.
- `pane move` takes the `pane_id` (like `w4:p3N`), not the `terminal_id` (like `term_...`).
