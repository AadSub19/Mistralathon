import { useEffect, useState } from 'react'
import type { RacePhase } from '../types'
import { getAudioStatus, onAudioStatus, type AudioStatus } from '../lib/commentary'

const PHASE_LABEL: Record<RacePhase, string> = {
  lobby: 'Lobby · Back your team',
  building: 'Building · Agents assembling',
  racing: 'Racing · Live',
  winner: 'Chequered flag',
}

function fmt(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000))
  const m = Math.floor(s / 60)
  const t = Math.floor((ms % 1000) / 100)
  return { mm: String(m).padStart(2, '0'), ss: String(s % 60).padStart(2, '0'), t }
}

export function RaceTimer({ startedAt, frozen }: { startedAt: number; frozen: boolean }) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    if (frozen) return
    const id = window.setInterval(() => setNow(Date.now()), 100)
    return () => window.clearInterval(id)
  }, [frozen])
  const { mm, ss, t } = fmt(now - startedAt)
  return (
    <div className="race-timer">
      {mm}:{ss}
      <small>.{t}</small>
    </div>
  )
}

interface Props {
  phase: RacePhase
  raceStartedAt: number | null
  audioOn: boolean
  onToggleAudio: () => void
  voxtral: boolean
}

export default function Header({ phase, raceStartedAt, audioOn, onToggleAudio, voxtral }: Props) {
  const live = phase === 'racing'
  const [status, setStatus] = useState<AudioStatus>(getAudioStatus())
  useEffect(() => onAudioStatus(setStatus), [])
  const label = !audioOn
    ? 'off'
    : status === 'blocked'
      ? 'blocked · click'
      : status === 'playing'
        ? 'speaking'
        : 'on'
  return (
    <header className="arena-header">
      <div className="brand">
        <div className="brand-title display">
          <span className="brand-mark" aria-hidden>
            {Array.from({ length: 12 }).map((_, i) => (
              <i key={i} />
            ))}
          </span>
          MISTRALATHON
        </div>
        <div className="brand-sub">PIZZA GRAND PRIX</div>
        <div className="brand-line">Three Mistral teams. One real-world challenge. First pizza through the door wins.</div>
      </div>

      <div className="header-center">
        {raceStartedAt && (phase === 'racing' || phase === 'winner') ? (
          <RaceTimer startedAt={raceStartedAt} frozen={phase === 'winner'} />
        ) : null}
        <div className={`phase-pill ${live ? 'live' : ''}`}>
          <i className="dot" />
          {PHASE_LABEL[phase]}
        </div>
      </div>

      <div className="header-right">
        <button
          className={`toggle ${audioOn ? 'on' : ''} ${status === 'blocked' ? 'blocked' : ''}`}
          onClick={onToggleAudio}
          title={voxtral ? 'Voxtral voice commentary' : 'Browser voice (set MISTRAL_API_KEY for Voxtral)'}
        >
          🎙 {voxtral ? 'Voxtral' : 'Commentary'} {label}
        </button>
      </div>
    </header>
  )
}
