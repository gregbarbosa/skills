import { expect, mock, test } from 'claude-code/testing'

import { askText, isHandoffFile, resumeText } from './register'

const FILE = '/home/user/.claude/handoffs/my-repo/2026-10-02-1530-mods.md'

test('knows a handoff file from other writes', () => {
  expect(isHandoffFile(FILE)).toBe(true)
  expect(isHandoffFile('/home/user/src/app/notes.md')).toBe(false)
})

test('the resume text matches what the user pastes after /compact', () => {
  expect(resumeText(FILE)).toBe(
    `Read ${FILE}. Run its Verify first checks; if they pass, set its status to consumed and resume from the first unchecked IN-FLIGHT item; if not, report the drift and wait.`,
  )
  expect(askText('focus on the SEO project')).toContain('focus on the SEO project')
})

test('the command writes, counts down, compacts, then resumes', async ($, on) => {
  const clock = mock.clock(on, { now: new Date(2026, 9, 2, 15, 30).getTime() })
  const sent: string[] = []
  const compacted: string[] = []
  on('prompt.submit', async (_$, e) => {
    sent.push((e as { text: string }).text)
    return { text: (e as { text: string }).text } as never
  })
  on('session.compact', async (_$, e) => {
    compacted.push((e as { instructions?: string }).instructions ?? '')
    return { messages: [{ role: 'user', text: 'summary', toolUses: [] }] } as never
  })
  on('tool.call', async () => ({ result: {} }) as never)
  on('turn.complete', async () => ({ text: '' }))
  on('ui.toast', async () => ({ value: undefined }) as never)

  await $.command.run({ command: 'handoff-compact', args: '' } as never)
  await clock.advance(0)
  expect(sent[0]).toContain('handoff skill')

  await $.tool.call({ tool: 'Write', file_path: FILE, content: '---' } as never)
  await $.turn.complete({ answer: 'saved', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as never)

  const ui = await $.ui.mount({
    plugin: 'handoff-compact',
    surface: 'terminal',
    component: 'AbovePrompt',
    props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 120 } as never,
  })
  expect(await ui.find({ text: /compacting in 10s/ })).toBeDefined()
  expect(compacted.length).toBe(0)

  await clock.advance(10_000)
  expect(compacted).toEqual([resumeText(FILE)])
  expect(sent.at(-1)).toBe(resumeText(FILE))
})

test('typing during the countdown stops it', async ($, on) => {
  const clock = mock.clock(on, { now: new Date(2026, 9, 2, 15, 30).getTime() })
  const compacted: string[] = []
  on('prompt.submit', async (_$, e) => ({ text: (e as { text: string }).text }) as never)
  on('session.compact', async (_$, e) => {
    compacted.push((e as { instructions?: string }).instructions ?? '')
    return { messages: [{ role: 'user', text: 'summary', toolUses: [] }] } as never
  })
  on('tool.call', async () => ({ result: {} }) as never)
  on('turn.complete', async () => ({ text: '' }))

  await $.command.run({ command: 'handoff-compact', args: '' } as never)
  await $.tool.call({ tool: 'Write', file_path: FILE, content: '---' } as never)
  await $.turn.complete({ answer: 'saved', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as never)
  await $.prompt.submit({ text: 'wait, one more thing', origin: { kind: 'composer' } } as never)
  await clock.advance(15_000)
  expect(compacted.length).toBe(0)
})
