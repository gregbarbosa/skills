import { expect, mock, test } from 'claude-code/testing'

import { askText, compactLine, isHandoffFile, isUnavailable, isUserPrompt, resumeText } from './register'

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

test('an automated message during the countdown defers it to the end of that turn', async ($, on) => {
  const clock = mock.clock(on, { now: new Date(2026, 9, 2, 15, 30).getTime() })
  const compacted: string[] = []
  on('prompt.submit', async (_$, e) => ({ text: (e as { text: string }).text }) as never)
  on('session.compact', async (_$, e) => {
    compacted.push((e as { instructions?: string }).instructions ?? '')
    return { messages: [{ role: 'user', text: 'summary', toolUses: [] }] } as never
  })
  on('tool.call', async () => ({ result: {} }) as never)
  on('turn.complete', async () => ({ text: '' }))
  on('ui.toast', async () => ({ value: undefined }) as never)

  await $.command.run({ command: 'handoff-compact', args: '' } as never)
  await $.tool.call({ tool: 'Write', file_path: FILE, content: '---' } as never)
  await $.turn.complete({ answer: 'saved', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as never)
  await clock.advance(5_000)
  await $.prompt.submit({ text: 'idle notice', origin: { kind: 'unclassified' } } as never)
  await clock.advance(15_000)
  expect(compacted.length).toBe(0)

  await $.turn.complete({ answer: 'noted', durationMs: 1, isAborted: false, turnId: 't2', reason: 'answer' } as never)
  await clock.advance(10_000)
  expect(compacted).toEqual([resumeText(FILE)])
})

test('a compact refused mid-turn starts again when the turn ends', async ($, on) => {
  const clock = mock.clock(on, { now: new Date(2026, 9, 2, 15, 30).getTime() })
  const compacted: string[] = []
  let busy = true
  on('prompt.submit', async (_$, e) => ({ text: (e as { text: string }).text }) as never)
  on('session.compact', async (_$, e) => {
    if (busy) throw new Error('a turn is running')
    compacted.push((e as { instructions?: string }).instructions ?? '')
    return { messages: [{ role: 'user', text: 'summary', toolUses: [] }] } as never
  })
  on('tool.call', async () => ({ result: {} }) as never)
  on('turn.complete', async () => ({ text: '' }))
  on('ui.toast', async () => ({ value: undefined }) as never)

  await $.command.run({ command: 'handoff-compact', args: '' } as never)
  await $.tool.call({ tool: 'Write', file_path: FILE, content: '---' } as never)
  await $.turn.complete({ answer: 'saved', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as never)
  await clock.advance(10_000)
  expect(compacted.length).toBe(0)

  busy = false
  await $.turn.complete({ answer: 'other', durationMs: 1, isAborted: false, turnId: 't2', reason: 'answer' } as never)
  await clock.advance(10_000)
  expect(compacted).toEqual([resumeText(FILE)])
})

test('an interrupted turn waits for a press instead of counting down', async ($, on) => {
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
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: true, turnId: 't1', reason: 'aborted' } as never)
  await clock.advance(15_000)
  expect(compacted.length).toBe(0)

  const ui = await $.ui.mount({
    plugin: 'handoff-compact',
    surface: 'terminal',
    component: 'AbovePrompt',
    props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 120 } as never,
  })
  expect(await ui.find({ text: /Compact now/ })).toBeDefined()
})

test('knows automated prompts from the user', () => {
  expect(isUserPrompt('composer')).toBe(true)
  expect(isUserPrompt('sdk')).toBe(true)
  expect(isUserPrompt(undefined)).toBe(true)
  expect(isUserPrompt('a-kind-from-a-later-build')).toBe(true)
  expect(isUserPrompt('unclassified')).toBe(false)
  expect(isUserPrompt('peer')).toBe(false)
})

test('a Remote Control message counts as the user and stops the countdown', async ($, on) => {
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
  await $.prompt.submit({ text: 'hold on', origin: { kind: 'bridge' } } as never)
  await $.turn.complete({ answer: 'ok', durationMs: 1, isAborted: false, turnId: 't2', reason: 'answer' } as never)
  await clock.advance(15_000)
  expect(compacted.length).toBe(0)
})

test('knows the refusal of a host that lets no mod compact', () => {
  expect(
    isUnavailable(new Error('HooksError: handoff-compact: $.session.compact: not available in a headless (-p) run')),
  ).toBe(true)
  expect(isUnavailable(new Error('a turn is running'))).toBe(false)
})

test('once the host refused, the next handoff puts /compact in the prompt box and resumes after it', async ($, on) => {
  const clock = mock.clock(on, { now: new Date(2026, 9, 2, 15, 30).getTime() })
  const sent: string[] = []
  const filled: string[] = []
  const compacted: string[] = []
  on('prompt.submit', async (_$, e) => {
    sent.push((e as { text: string }).text)
    return { text: (e as { text: string }).text } as never
  })
  on('prompt.fill', async (_$, e) => {
    filled.push((e as { text: string }).text)
    return { isFilled: true } as never
  })
  on('session.compact', async (_$, e) => {
    compacted.push((e as { instructions?: string }).instructions ?? '')
    return { messages: [{ role: 'user', text: 'summary', toolUses: [] }] } as never
  })
  on('tool.call', async () => ({ result: {} }) as never)
  on('turn.complete', async () => ({ text: '' }))
  on('ui.toast', async () => ({ value: undefined }) as never)

  // An earlier refusal in this session, as the state holds it.
  let seeded = false
  on('state.set', async (_$, e, next) => {
    if ((e as { key?: string }).key === 'noCompact') seeded = false
    return next(e)
  })
  on('state.get', async (_$, e, next) => {
    const got = await next(e)
    if ((e as { key?: string }).key === 'noCompact' && !seeded) return { ...got, value: { ...(got as { value: object }).value, value: true } } as never
    return got
  })
  await $.command.run({ command: 'handoff-compact', args: '' } as never)
  await $.tool.call({ tool: 'Write', file_path: FILE, content: '---' } as never)
  await $.turn.complete({ answer: 'saved', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as never)
  await clock.advance(15_000)
  expect(filled).toEqual([compactLine(FILE)])
  expect(compacted.length).toBe(0)

  const ui = await $.ui.mount({
    plugin: 'handoff-compact',
    surface: 'terminal',
    component: 'AbovePrompt',
    props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 120 } as never,
  })
  expect(await ui.find({ text: /run \/compact/ })).toBeDefined()

  await $.session.compact({ instructions: resumeText(FILE), messages: [{ role: 'user', text: 'earlier', toolUses: [] }] } as never)
  await clock.advance(0)
  expect(sent.at(-1)).toBe(resumeText(FILE))
})
