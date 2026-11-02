import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Pending } from '../types'

const COUNTDOWN_MS = 10_000
// Messages no person typed. Any other origin, unknown ones included, counts as the user and cancels.
const AUTOMATED_ORIGINS = new Set([
  'task-notification',
  'scheduled-trigger',
  'peer',
  'peer-send-message',
  'projects-relay',
  'coordinator',
  'observer',
  'observer-activity',
  'plugin',
  'unclassified',
])
const isArmed = atom({ plugin: 'handoff-compact', key: 'isArmed' } as const, false)
const pending = atom({ plugin: 'handoff-compact', key: 'pending' } as const, null)
const now = atom({ plugin: 'handoff-compact', key: 'now' } as const, 0)

export const isHandoffFile = (path: string) => /\/\.claude\/handoffs\/.+\.md$/.test(path)

export const isUserPrompt = (kind: string | undefined) => kind === undefined || !AUTOMATED_ORIGINS.has(kind)

export const baseName = (path: string) => path.split('/').pop() ?? path

// The same text the handoff skill tells the user to paste after /compact.
export const resumeText = (path: string) =>
  `Read ${path}. Run its Verify first checks; if they pass, set its status to consumed and resume from the first unchecked IN-FLIGHT item; if not, report the drift and wait.`

export const askText = (notes: string) =>
  [
    'Run the handoff skill now (Skill tool, skill "handoff").',
    notes ? `Context from the user for the handoff: ${notes}` : '',
    'Save the handoff with the Write tool; the mod watches that tool to find the file.',
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

async function startCountdown($: EngineInterface, held: Pending) {
  stopTimers()
  const start = await $.clock.now()
  await update($, now, () => start)
  await update($, pending, () => ({ ...held, autoAt: start + COUNTDOWN_MS, retry: false }))
  timers.push($.clock.every(1000, () => void $.clock.now().then(t => update($, now, () => t))))
  timers.push($.clock.after(COUNTDOWN_MS, () => void compactNow($)))
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
    // Most often a turn is running: an automated message arrived during the countdown.
    await update($, pending, () => ({ ...held, autoAt: null, retry: true }))
    $.ui.toast(`Could not compact yet (${String(error).slice(0, 80)}). The countdown starts again when the next turn ends.`, {
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
  // An automated message (a notification, another session) only defers the countdown to the end of its turn.
  on('prompt.submit', async ($, e, next) => {
    const held = await read($, pending)
    if (isUserPrompt(e.origin?.kind)) {
      if (held?.autoAt || held?.retry) {
        stopTimers()
        await update($, pending, () => ({ ...held, autoAt: null, retry: false }))
      }
      await update($, isArmed, () => false)
    } else if (held?.autoAt) {
      stopTimers()
      await update($, pending, () => ({ ...held, autoAt: null, retry: true }))
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    if (e.agentId) return done

    const armed = await read($, isArmed)
    const held = await read($, pending)
    if (!armed && !held?.retry) return done
    await update($, isArmed, () => false)
    if (!held) {
      $.ui.toast('No handoff file was written, so nothing was compacted.', { timeoutMs: 8000 })
      return done
    }
    // An interrupted or failed turn waits for a press: the user may want to look first.
    if (e.reason !== 'answer') {
      await update($, pending, () => ({ ...held, autoAt: null, retry: false }))
      return done
    }
    await startCountdown($, held)
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
