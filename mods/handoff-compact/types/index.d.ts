export type Pending = {
  path: string
  // When the countdown compacts on its own; null waits for a press.
  autoAt: number | null
}

declare module 'claude-code' {
  interface PluginState {
    'handoff-compact': { isArmed: boolean; pending: Pending | null; now: number }
  }
}
