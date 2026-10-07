"""The handoff skill and the handoff-compact mod must send the same resume text.

The skill tells the user to paste it after /compact; the mod sends it itself.
Mod tests cannot read files outside the mod, so the check lives here.
Run from the repo root: python3 -m unittest discover tests
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class HandoffResumeText(unittest.TestCase):
    def test_skill_and_mod_agree(self):
        mod = read("mods", "handoff-compact", "hooks", "register.tsx")
        m = re.search(r"export const resumeText = \(path: string\) =>\s*`([^`]*)`", mod)
        self.assertIsNotNone(m, "resumeText not found in register.tsx")
        expected = "/compact " + m.group(1).replace("${path}", "<absolute path>")
        skill = read("skills", "handoff", "SKILL.md")
        self.assertIn(expected, skill)


if __name__ == "__main__":
    unittest.main()
