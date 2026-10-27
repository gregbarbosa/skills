---
name: afk
description: Use when the user types /afk, says they are away from keyboard, stepping away, going to bed, or "keep going without me", and wants the current work carried through to its end so that the only thing left for them is one final approval (a merge, a release, a publish).
---

# AFK: carry the work to one final approval

The user has left. Every stop that waits on them now costs hours. Work until the
whole task in this conversation reaches its **final gate**: the one action that
needs their consent. Then leave one question.

`/afk` is not consent for anything the rules already reserve for the user. It is
consent to keep working, decide reversible things yourself, and not stop early.

## 1. Name the finish line first

Before any other step, write down in one line what "done" is for the work in this
conversation and what the final gate is. Pick the gate the project's own flow
ends in:

| The work is | The final gate is |
|---|---|
| A feature or fix on a branch | Merge of the verified PR |
| A batch of merged changes waiting to ship | Merge of the release PR, or the release command |
| A doc, plan or research | Merge of its PR, or the user's read of the file |
| A spike or measurement | The user's decision on the numbers |

Everything before that gate is yours: build, test, push, open the PR, get the
verifier's verdict, fix what the verdict or CI finds, merge `main` into the
branch, update CHANGELOG and docs.

## 2. Keep going

Loop until only the final gate is left:

1. Do the next step of the finish line.
2. When a step waits on something slow (a child session, CI, a long build), make
   sure something will wake you: a child session's end, a `run_in_background`
   command that exits when the condition is met, or a Monitor. Then end the turn.
   Never end a turn with nothing armed to wake you, unless only the gate is left.
3. When you wake, read what arrived, verify it (a session's report is not proof),
   and go back to 1.

Context fills up: the harness compacts and you continue. Do not stop to write a
handoff instead of working. If you keep a plan or progress file, update it.

## 3. Decide instead of asking

| You meet | Do this |
|---|---|
| A reversible choice (naming, a default value, which of two fixes) | Pick the option you would recommend. Write it down as an assumption in the PR or the final report. Continue. |
| A product call the rules reserve for the user, and other work does not depend on it | Pick the safe, reversible default, mark it clearly for the user, and finish everything else. |
| A product call that blocks all remaining work | Finish every part that does not depend on it, then make it the final question. |
| A step that failed 2 to 3 times | Stop that step, record what you tried, and continue with the steps that do not depend on it. |
| Unpushed commits on a branch with an open PR | Push them, if the project lets you push without asking. |

## 4. What `/afk` never permits

These still wait for the user, exactly as the project's rules say: a merge, a
release, a publish or anything else outward-facing that needs consent; deleting
data you did not create; force-push or rebase; spending money; anything a
security or permission rule forbids. Prepare them completely so that the user's
part is one action.

## 5. The final message

The last message holds:

1. **Done:** what is now true, with PR and commit links.
2. **Assumptions:** each decision you made for the user, one line each.
3. **Not done:** anything that failed or that you could not verify, with the reason.
4. **One question:** the final gate (for example, "Merge PR #340?"). Put it in the
   app's wrap-up box when the app has one.

Write it only when nothing armed can still change it; until then, end each turn
with one status line instead. One gate, one question. If two things wait on the user, the second one is a
failure of step 3; go back and decide it, or finish around it.

## Red flags: you are about to stop early

- "I'll leave the push / the README / the flaky test for when they're back."
- "The child session reports in 70 minutes, so I'll stop here."
- "Context is getting full, I'll write a handoff and stop."
- "Here are three next steps for you."
- "Want me to…?"

Each one means: go back to section 2.
