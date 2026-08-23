import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api, participantId } from '../api'
import { TEAMS, TEAM_LIST } from '../teams'
import type { RacePhase, TeamId } from '../types'

const NAME_KEY = 'mistralathon_name'

export default function Join() {
  const pid = participantId()
  const [name, setName] = useState(() => {
    try {
      return localStorage.getItem(NAME_KEY) ?? ''
    } catch {
      return ''
    }
  })
  const [team, setTeam] = useState<TeamId | null>(null)
  const [backed, setBacked] = useState<TeamId | null>(null)
  const [locked, setLocked] = useState(false)
  const [phase, setPhase] = useState<RacePhase>('lobby')
  const [winner, setWinner] = useState<TeamId | null>(null)
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    document.body.classList.add('join-body')
    return () => document.body.classList.remove('join-body')
  }, [])

  // Poll my record + lock state so the phone follows the host.
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const r = await api.mySupport(pid)
        if (!alive) return
        setLocked(r.picksLocked)
        setPhase(r.racePhase)
        setWinner(r.winner)
        if (r.supporter) {
          setBacked(r.supporter.team)
          if (!editing) setTeam(r.supporter.team)
        } else if (backed) {
          setBacked(null) // host reset
          setEditing(false)
        }
      } catch {
        /* keep last known */
      }
      if (alive) window.setTimeout(tick, 2000)
    }
    tick()
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pid, editing])

  const submit = async () => {
    if (!team || !name.trim()) return
    setBusy(true)
    setErr(null)
    try {
      localStorage.setItem(NAME_KEY, name.trim())
    } catch {
      /* ignore */
    }
    try {
      const r = await api.support(pid, name.trim(), team)
      setBacked(r.supporter.team)
      setEditing(false)
    } catch (e) {
      const m = (e as Error).message
      setErr(m === 'Picks are locked' ? 'Picks are locked — the race is on.' : m || 'Could not reach the arena.')
      if (m === 'Picks are locked') setLocked(true)
    } finally {
      setBusy(false)
    }
  }

  const showForm = !backed || editing

  return (
    <div className="join">
      <div>
        <div className="join-brand display">
          <span className="brand-mark" aria-hidden>
            {Array.from({ length: 12 }).map((_, i) => (
              <i key={i} />
            ))}
          </span>
          MISTRALATHON
        </div>
        <div className="join-sub">PIZZA GRAND PRIX</div>
      </div>

      <AnimatePresence mode="wait">
        {winner ? (
          <Result key="winner" team={winner} mine={backed} />
        ) : showForm ? (
          <motion.div key="form" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
            <h1 className="join-q display">Who are you backing?</h1>

            <label className="join-field">
              <span className="eyebrow">Your name</span>
              <input
                className="join-input"
                placeholder="First name"
                value={name}
                maxLength={24}
                autoComplete="given-name"
                onChange={(e) => setName(e.target.value)}
                disabled={locked}
              />
            </label>

            <div className="choices">
              {TEAM_LIST.map((t) => (
                <motion.button
                  key={t.id}
                  className={`choice ${team === t.id ? 'on' : ''}`}
                  style={{ ['--team' as string]: t.color, ['--team-soft' as string]: t.colorSoft }}
                  whileTap={locked ? undefined : { scale: 0.985 }}
                  onClick={() => !locked && setTeam(t.id)}
                  disabled={locked}
                >
                  <span className="choice-glyph">{t.glyph}</span>
                  <span>
                    <div className="choice-name">{t.name.charAt(0) + t.name.slice(1).toLowerCase()}</div>
                    <div className="choice-title">{t.title}</div>
                  </span>
                  <i className="choice-check" />
                </motion.button>
              ))}
            </div>

            {locked ? (
              <div className="join-err">Picks are locked — the race is on. Watch the big screen.</div>
            ) : (
              <button className="join-btn" disabled={!team || !name.trim() || busy} onClick={submit}>
                {busy ? '…' : 'BACK THIS TEAM'}
              </button>
            )}
            {err && <div className="join-err">{err}</div>}
            {backed && editing && !locked && (
              <button className="link-btn" onClick={() => setEditing(false)}>
                Keep {TEAMS[backed].name}
              </button>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="done"
            className="join-done"
            style={{ ['--team' as string]: TEAMS[backed!].color }}
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          >
            <motion.div className="join-done-glyph" initial={{ scale: 0.4, rotate: -20 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: 'spring', stiffness: 260, damping: 14 }}>
              {TEAMS[backed!].glyph}
            </motion.div>
            <h1 className="join-done-h display">
              You’re backing <span>{TEAMS[backed!].name}</span>
            </h1>
            <p className="join-done-p">Now watch the Mistralathon.</p>
            {phase === 'racing' && <p className="join-done-p mono" style={{ fontSize: 13 }}>🏁 The Pizza Agents are live.</p>}
            {!locked ? (
              <button className="link-btn" onClick={() => setEditing(true)}>
                Change my pick
              </button>
            ) : (
              <span className="eyebrow">Picks locked</span>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Result({ team, mine }: { team: TeamId; mine: TeamId | null }) {
  const t = TEAMS[team]
  const won = mine === team
  return (
    <motion.div key="result" className="join-done" style={{ ['--team' as string]: t.color }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <div className="join-done-glyph">🏆</div>
      <h1 className="join-done-h display">
        <span>{t.name}</span> wins the Pizza Grand Prix
      </h1>
      <p className="join-done-p">{won ? 'You called it.' : mine ? `You backed ${TEAMS[mine].name}. Next time.` : 'Thanks for watching.'}</p>
    </motion.div>
  )
}
