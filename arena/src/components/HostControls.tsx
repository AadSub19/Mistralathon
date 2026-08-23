import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../api'
import { TEAM_LIST } from '../teams'
import type { ArenaState, RacePhase } from '../types'

const PHASES: RacePhase[] = ['lobby', 'building', 'racing']

export default function HostControls({ state }: { state: ArenaState }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    try {
      await fn()
    } finally {
      setBusy(false)
    }
  }
  const srcLine = (Object.keys(state.eventSources) as Array<keyof typeof state.eventSources>)
    .map((t) => `${t}:${state.eventSources[t]}`)
    .join(' ')

  return (
    <>
      <button className="host-fab" onClick={() => setOpen((o) => !o)} title="Host controls">
        ⚙
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="host-panel"
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.18 }}
          >
            <div className="host-section">
              <span className="eyebrow">Race phase</span>
              <div className="seg">
                {PHASES.map((p) => (
                  <button key={p} className={state.racePhase === p ? 'on' : ''} disabled={busy} onClick={() => run(() => api.phase(p))}>
                    {p}
                  </button>
                ))}
              </div>
            </div>

            <div className="host-section">
              <span className="eyebrow">Audience</span>
              <button className="host-btn" disabled={busy} onClick={() => run(() => api.lock(!state.picksLocked))}>
                {state.picksLocked ? '🔓 Unlock picks' : '🔒 Lock picks'} · {state.supporters.length} backing
              </button>
            </div>

            <div className="host-section">
              <span className="eyebrow">Declare winner</span>
              <div className="seg">
                {TEAM_LIST.map((t) => (
                  <button key={t.id} className={state.winner === t.id ? 'on' : ''} disabled={busy} onClick={() => run(() => api.winner(t.id))}>
                    {t.glyph} {t.name}
                  </button>
                ))}
              </div>
              {state.winner && (
                <button className="host-btn" disabled={busy} onClick={() => run(() => api.winner(null))}>
                  Undo winner
                </button>
              )}
            </div>

            <div className="host-section">
              <button
                className="host-btn danger"
                disabled={busy}
                onClick={() => {
                  if (window.confirm('Reset supporters, phase, winner and mock events?')) run(() => api.reset())
                }}
              >
                Reset arena
              </button>
              <span className="host-note">events → {srcLine}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
