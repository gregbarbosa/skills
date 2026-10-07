"""Tests for field.py brief: the rendered contract must not drift.

The oracle strings are the brief exactly as the skills carried it before
`field.py brief` existed (field-handler/SKILL.md, 2026-10-07), with the
placeholders left in. A change to the contract wording fails here first.
Run: python3 -m unittest test_field.py (stdlib only).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import field  # noqa: E402

BLOCKS_ORACLE = "Field agent brief from your handler.\n\n<task>\n<task>. Scope and read first; flag any irreversible change before you make it.\n</task>\n\n<context>\nRead these first, in this order:\n- <absolute path to the CLAUDE.md or AGENTS.md of the repo the task concerns>\n- <absolute path to the README, spec, plan, or prior deliverable the task builds on>\nFacts you can rely on:\n- <a decision, number, or gotcha already established, one per line>\nCredentials and access:\n- <where a key or token comes from: a path or a command, never the value>\nConventions:\n- <no em-dashes; do not git add, commit, or change branch; the rules of this repo>\n</context>\n\n<identity>\nYou are field agent '<agent_name>' in herdr pane <pane_id>. Your handler is agent 'm'.\n</identity>\n\n<report_command>\nherdr agent prompt 'm' 'FIELD REPORT <agent_name>: <your message>'\n</report_command>\n\n<report_moments>\nRun the report command at these four moments, not only at the end:\n(1) START, one line when you understand the task and begin\n(2) MILESTONE, one line each time you finish a meaningful unit, or roughly every 15 minutes of work\n(3) BLOCKED, immediately if you need a decision, a credential, or an answer, and state the exact question\n(4) COMPLETE, when you finish, with the verdict, every file path you changed, the branch name, and the test or build result\n</report_moments>\n\n<complete_prefix>\nFIELD REPORT <agent_name>: COMPLETE:\n</complete_prefix>\n\n<time>\nStarted <HH:MM from date>. Budget about <N> minutes, advisory: check date at each milestone and pace to finish inside it. Time matters here: do not spend time that can be avoided, and the earlier a correct result is obtained, the better.\n</time>\n\n<rules>\nThe report command is the only way your work reaches anyone.\nSend the COMPLETE report and the notification as ONE command: herdr agent prompt 'm' 'FIELD REPORT <agent_name>: COMPLETE: ...' && herdr notification show 'Field agent done: <agent_name>' --sound done\nYour COMPLETE report is your final message. Do not write a second summary in the pane after it.\nYour turn ends only with a COMPLETE or a BLOCKED report. Do not stop on a summary that announces the next step, an offer to continue unless told otherwise, a list of decisions that block nothing, or a milestone that feels like a good place to report. Send the MILESTONE report in the same message as your next tool call and keep working. Before a risky or irreversible action, report BLOCKED and wait.\nBefore you change anything, read the files that the task can depend on, including files that this brief does not name.\nKeep the parts of your task as a checklist in ~/.claude/field/checklists/<agent_name>.md (create it at START). Tick each item when it is done. Send COMPLETE only when every item is ticked; otherwise send BLOCKED and name the open items.\nIf your report command fails, retry it twice before you continue.\nReport what you actually found. If the task rests on a wrong assumption, say so instead of working around it.\nDo not ask the human directly. Route every question through your handler.\n</rules>"

LINE_ORACLE = "Field agent brief from your handler.  ||  <task>. Scope and read first; flag any irreversible change before you make it.  ||  CONTEXT, read these first: <absolute paths>. Facts you can rely on: <facts>. Credentials: <where they come from, never the value>. Conventions: <rules>.  ||  === FIELD AGENT BRIEF ===  ||  You are field agent '<agent_name>' in herdr pane <pane_id>. Your handler is agent 'm'.  ||  REPORT TO YOUR HANDLER by running this command, this is the only way your work reaches anyone:  herdr agent prompt 'm' 'FIELD REPORT <agent_name>: <your message>'  ||  Report at these four moments, not only at the end: (1) START, one line when you understand the task and begin; (2) MILESTONE, one line each time you finish a meaningful unit, or roughly every 15 minutes of work; (3) BLOCKED, immediately if you need a decision, a credential, or an answer, and state the exact question; (4) COMPLETE, when you finish, with the verdict, every file path you changed, the branch name, and the test or build result.  ||  Prefix the final one with 'FIELD REPORT <agent_name>: COMPLETE:' and send it and the notification as ONE command: herdr agent prompt 'm' 'FIELD REPORT <agent_name>: COMPLETE: ...' && herdr notification show 'Field agent done: <agent_name>' --sound done  ||  Your COMPLETE report is your final message; do not write a second summary after it.  ||  Your turn ends only with a COMPLETE or a BLOCKED report. Do not stop on a summary that announces the next step, an offer to continue unless told otherwise, a list of decisions that block nothing, or a milestone that feels like a good place to report. Send the MILESTONE report in the same message as your next tool call and keep working. Before a risky or irreversible action, report BLOCKED and wait.  ||  Before you change anything, read the files that the task can depend on, including files that this brief does not name.  ||  Keep the parts of your task as a checklist in ~/.claude/field/checklists/<agent_name>.md (create it at START). Tick each item when it is done. Send COMPLETE only when every item is ticked; otherwise send BLOCKED and name the open items.  ||  Started <HH:MM>; budget about <N> minutes, advisory; time matters, so the earlier a correct result, the better.  ||  If your report command fails, retry it twice before you continue.  ||  Report what you actually found. If the task rests on a wrong assumption, say so instead of working around it.  ||  Do not ask the human directly. Route every question through your handler."

CONTEXT = BLOCKS_ORACLE.split("<context>\n")[1].split("\n</context>")[0]


class BriefTest(unittest.TestCase):
    def test_blocks_form_matches_the_tuned_text(self):
        got = field.render_brief(
            "<agent_name>", "<pane_id>", "m", "<task>." + field.SCOPED,
            context=CONTEXT, budget="<N>", started="<HH:MM from date>",
            fmt="blocks")
        self.assertEqual(got, BLOCKS_ORACLE)

    def test_line_form_matches_the_tuned_text(self):
        # The line form's CONTEXT part is free text the handler supplies, so
        # compare everything else.
        parts = LINE_ORACLE.split("  ||  ")
        expected = "  ||  ".join(p for p in parts if not p.startswith("CONTEXT,"))
        got = field.render_brief(
            "<agent_name>", "<pane_id>", "m", "<task>." + field.SCOPED,
            budget="<N>", started="<HH:MM>", fmt="line")
        self.assertEqual(got, expected)

    def test_line_form_flattens_context(self):
        got = field.render_brief("a", "w1:p1", "m", "do it",
                                 context="Read:\n- /x/README.md\n- /x/spec.md",
                                 fmt="line")
        self.assertIn("  ||  CONTEXT: Read: /x/README.md /x/spec.md  ||  ", got)

    def test_no_budget_keeps_only_the_time_sentence(self):
        got = field.render_brief("a", "w1:p1", "m", "do it", fmt="blocks")
        self.assertIn("<time>\n" + field.TIME_MATTERS + "\n</time>", got)
        self.assertNotIn("<context>", got)

    def test_identity_never_carries_the_handler_pane(self):
        for fmt in ("blocks", "line"):
            got = field.render_brief("a", "w1:p1", "m", "do it", fmt=fmt)
            self.assertIn("Your handler is agent 'm'.", got)
            self.assertNotIn("Your handler is agent 'm' in pane", got)


if __name__ == "__main__":
    unittest.main()
