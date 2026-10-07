import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Pending } from '../types'

const COUNTDOWN_MS = 10_000
const isArmed = atom({ plugin: 'handoff-compact', key: 'isArmed' } as const, false)
const pending = atom({ plugin: 'handoff-compact', key: 'pending' } as const, null)
const now = atom({ plugin: 'handoff-compact', key: 'now' } as const, 0)

export const isHandoffFile = (path: string) => /\/\.claude\/handoffs\/.+\.md$/.test(path)

export const baseName = (path: string) => path.split('/').pop() ?? path

// The same text the handoff skill tells the user to paste after /compact.
export const resumeText = (path: string) =>
  `Read ${path}. Run its Verify first checks; if they pass, set its status to consumed, create one task per IN-FLIGHT item with the task tool, and resume from the first task; if not, report the drift and wait.`

export const askText = (notes: string) =>
  [
    'Run the handoff skill now (Skill tool, skill "handoff").',
    notes ? `Context from the user for the handoff: ${notes}` : '',
    'Skip its last step: the handoff-compact mod runs /compact and the resume prompt for you once your turn ends, so end the turn as soon as the file is saved and printed.',
  ]
    .filter(Boolean)
    .join('\n')

// Timers live with this load; a reload drops a running countdown, and the band offers the button instead.
let timers: { cancel: () => void }[] = []

function stopTimers() {
  for (const timer of timers) timer.cancel()
  timers = []
}

async function compactNow($: EngineInterface) {
  stopTimers()
  const held: Pending | null = await read($, pending)
  if (!held) return
  await update($, pending, () => ({ ...held, autoAt: null }))
  try {
    const done = await $.session.compact({ instructions: resumeText(held.path) })
    if (done && 'skip' in done && done.skip) {
      $.ui.toast('Compaction was vetoed by another hook; the handoff is still saved.')
      return
    }
    await update($, pending, () => null)
    void $.prompt.submit({ text: resumeText(held.path) })
  } catch (error) {
    $.ui.toast(`Could not compact yet (${String(error).slice(0, 80)}). Press Compact now when the turn ends.`, {
      timeoutMs: 8000,
    })
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    stopTimers()
    await $.command.register({
      name: 'handoff-compact',
      description: 'Write a handoff, compact with its resume instructions, then resume (optional notes for the handoff)',
    })
    // A countdown cut off by a reload waits for a press instead.
    const held = await read($, pending)
    if (held?.autoAt) await update($, pending, () => ({ ...held, autoAt: null }))
    return started
  })

  on('command.run', { command: 'handoff-compact' }, async ($, e) => {
    stopTimers()
    await update($, isArmed, () => true)
    await update($, pending, () => null)
    // A command may not submit while it answers; the timer submits right after.
    const ask = askText(e.args.trim())
    timers.push($.clock.after(0, () => void $.prompt.submit({ text: ask })))
    return { text: 'Writing the handoff. It compacts 10 seconds after the file is saved; type anything to stop it.' }
  })

  on('tool.call', { tool: 'Write' }, async ($, e, next) => {
    const result = await next(e)
    const path = String((e as { file_path?: string }).file_path ?? '')
    const failed = ('deny' in result && result.deny) || ('isError' in result && result.isError)
    if (!e.agentId && !failed && isHandoffFile(path)) {
      await update($, pending, () => ({ path, autoAt: null }))
    }
    return result
  })

  // Anything the user types takes over: no compaction happens behind their back.
  on('prompt.submit', async ($, e, next) => {
    if (e.origin?.kind === 'composer') {
      const held = await read($, pending)
      if (held?.autoAt) {
        stopTimers()
        await update($, pending, () => ({ ...held, autoAt: null }))
      }
      await update($, isArmed, () => false)
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId) return done

    const armed = await read($, isArmed)
    const held = await read($, pending)
    if (armed) {
      await update($, isArmed, () => false)
      if (!held) {
        $.ui.toast('No handoff file was written, so nothing was compacted.', { timeoutMs: 8000 })
        return done
      }
      const start = await $.clock.now()
      await update($, now, () => start)
      await update($, pending, () => ({ ...held, autoAt: start + COUNTDOWN_MS }))
      stopTimers()
      timers.push($.clock.every(1000, () => void $.clock.now().then(t => update($, now, () => t))))
      timers.push($.clock.after(COUNTDOWN_MS, () => void compactNow($)))
    }
    return done
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const held = await read($, pending)
    if (e.props.hasSurvey || !held || e.props.isWorking) return next(e)

    const { Box, Button, Text } = $.ui.resolve(e)
    const left = held.autoAt ? Math.max(0, Math.ceil((held.autoAt - (await read($, now))) / 1000)) : null

    return (
      <Box flexDirection="row" paddingX={1}>
        <Text color="cyan" bold>
          Handoff saved:{' '}
        </Text>
        <Text>{baseName(held.path)}</Text>
        <Text dimColor>{left === null ? '  ' : `  compacting in ${left}s  `}</Text>
        <Button key="now" label="Compact now" onPress={() => void compactNow($)} />
        <Text> </Text>
        <Button
          key="drop"
          label={left === null ? 'Dismiss' : 'Cancel'}
          onPress={async () => {
            stopTimers()
            await update($, pending, () => null)
          }}
        />
      </Box>
    )
  })
}
