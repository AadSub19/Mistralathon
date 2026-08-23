import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, animate, motion, useMotionValue } from 'framer-motion'
import type { TeamMeta } from '../teams'
import type { RaceEvent, RacePhase, Supporter } from '../types'
import { progress, recentActivity } from '../lib/translate'
import BlitzMotif from './motifs/BlitzMotif'
import OracleMotif from './motifs/OracleMotif'
import MaverickMotif from './motifs/MaverickMotif'

interface Props {
  team: TeamMeta
  supporters: Supporter[]
  events: RaceEvent[]
  phase: RacePhase
  dimmed: boolean
  winner: boolean
}

/** Per-team hover physics: three different personalities, not three colours. */
const HOVER = {
  blitz: {
    whileHover: { y: -10, scale: 1.025, skewX: -1.5 },
    transition: { type: 'spring' as const, stiffness: 520, damping: 22, mass: 0.6 },
  },
  oracle: {
    whileHover: { y: -8, scale: 1.02 },
    transition: { type: 'spring' as const, stiffness: 120, damping: 20, mass: 1.1 },
  },
  maverick: {
    whileHover: { y: -9, scale: 1.02, rotate: -1.2, x: 4 },
    transition: { type: 'spring' as const, stiffness: 260, damping: 9, mass: 0.9 },
  },
}

function Counter({ value }: { value: number }) {
  const mv = useMotionValue(value)
  const [shown, setShown] = useState(value)
  useEffect(() => {
    const c = animate(mv, value, { duration: 0.7, ease: [0.2, 0.8, 0.2, 1], onUpdate: (v) => setShown(Math.round(v)) })
    return () => c.stop()
  }, [value, mv])
  return <span className="sup-count">{shown}</span>
}

export default function TeamCard({ team, supporters, events, phase, dimmed, winner }: Props) {
  const [hover, setHover] = useState(false)
  const [pulseKey, setPulseKey] = useState(0)
  const [newest, setNewest] = useState<string | null>(null)
  const prevCount = useRef(supporters.length)
  const prevIds = useRef(new Set(supporters.map((s) => s.id)))

  useEffect(() => {
    const count = supporters.length
    if (count > prevCount.current) {
      const fresh = supporters.find((s) => !prevIds.current.has(s.id)) ?? supporters[supporters.length - 1]
      setNewest(fresh?.name ?? null)
      setPulseKey((k) => k + 1)
      const t = window.setTimeout(() => setNewest(null), 2600)
      prevCount.current = count
      prevIds.current = new Set(supporters.map((s) => s.id))
      return () => window.clearTimeout(t)
    }
    prevCount.current = count
    prevIds.current = new Set(supporters.map((s) => s.id))
  }, [supporters])

  const mode = phase === 'building' ? 'build' : phase === 'racing' || phase === 'winner' ? 'race' : null
  const acts = mode ? recentActivity(events, 4) : []
  const lit = mode ? progress(events, mode) : 0
  const active = hover || winner
  const names = [...supporters].sort((a, b) => b.ts - a.ts)
  const shown = names.slice(0, 4).map((s) => s.name.split(' ')[0])
  const extra = names.length - shown.length

  const Motif = team.id === 'blitz' ? BlitzMotif : team.id === 'oracle' ? OracleMotif : MaverickMotif
  const hv = HOVER[team.id]

  return (
    <motion.div
      className="card"
      style={{ ['--team' as string]: team.color, borderColor: active ? team.color : undefined }}
      animate={{ opacity: dimmed ? 0.28 : 1, scale: dimmed ? 0.97 : 1 }}
      whileHover={dimmed ? undefined : hv.whileHover}
      transition={hv.transition}
      onHoverStart={() => setHover(true)}
      onHoverEnd={() => setHover(false)}
    >
      <Motif active={active} color={team.color} />

      <AnimatePresence>
        {pulseKey > 0 && (
          <motion.div
            key={pulseKey}
            className="pulse-ring"
            initial={{ opacity: 0.9, scale: 1 }}
            animate={{ opacity: 0, scale: 1.06 }}
            transition={{ duration: 0.9, ease: 'easeOut' }}
          />
        )}
      </AnimatePresence>

      <motion.div
        key={`flash-${pulseKey}`}
        className="card-accent"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: pulseKey ? 0.5 : 1.2, ease: [0.2, 0.8, 0.2, 1] }}
      />

      <div className="card-body">
        <div className="card-top">
          <motion.span
            className="card-glyph"
            animate={
              team.id === 'blitz'
                ? { x: active ? [0, 3, -2, 0] : 0 }
                : team.id === 'oracle'
                  ? { rotate: active ? [0, 6, -6, 0] : 0, scale: active ? 1.08 : 1 }
                  : { rotate: active ? [0, -14, 10, 0] : 0, y: active ? [0, -4, 0] : 0 }
            }
            transition={{ duration: team.id === 'blitz' ? 0.35 : 1.4, repeat: active ? Infinity : 0, repeatDelay: team.id === 'blitz' ? 0.2 : 0.6 }}
          >
            {team.glyph}
          </motion.span>
          <span className="card-index">TEAM {team.index}</span>
        </div>

        <h2 className="card-name display" style={{ letterSpacing: active ? (team.id === 'blitz' ? '0.04em' : team.id === 'maverick' ? '0.02em' : '0em') : '-0.01em' }}>
          {team.name}
        </h2>
        <div className="card-title" style={{ color: team.color }}>
          {team.title}
        </div>
        <p className="card-tagline">{team.tagline}</p>

        {!mode && <div className="card-ghost" aria-hidden>{team.index}</div>}
        <div className="card-mid">
          {mode && (
            <>
              <div className="progress" aria-label={`${lit} of 6 milestones`}>
                {Array.from({ length: 6 }).map((_, i) => (
                  <i key={i} style={i < lit ? { background: team.color, boxShadow: `0 0 12px ${team.color}66` } : undefined} />
                ))}
              </div>
              <div className="activity">
                <AnimatePresence initial={false}>
                  {acts.length === 0 && (
                    <motion.div key="idle" className="activity-row" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                      <i className="tick" />
                      <span>{mode === 'build' ? 'Awaiting first move' : 'On the grid'}</span>
                    </motion.div>
                  )}
                  {acts.map((a, i) => (
                    <motion.div
                      key={a.key}
                      className={`activity-row ${i === acts.length - 1 ? 'latest' : ''} ${a.kind === 'milestone' ? 'milestone' : ''}`}
                      initial={{ opacity: 0, x: team.id === 'maverick' ? 18 : -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.35 }}
                      layout
                    >
                      <i className="tick" />
                      <span>{a.label}</span>
                      {a.detail && <span className="detail">{a.detail}</span>}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </>
          )}
        </div>

        <div className="card-bottom">
          <div className="sup-row">
            <Counter value={supporters.length} />
            <span className="sup-label">{supporters.length === 1 ? 'supporter' : 'supporters'}</span>
            <AnimatePresence>
              {newest && (
                <motion.span
                  key={newest + pulseKey}
                  className="sup-new"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                >
                  + {newest}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
          <div className="sup-names">
            {shown.length === 0 ? <em>Be the first to back {team.name.charAt(0) + team.name.slice(1).toLowerCase()}</em> : shown.join(' · ')}
            {extra > 0 && <em> · +{extra}</em>}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
