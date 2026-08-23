import { useEffect, useMemo } from 'react'
import { AnimatePresence } from 'framer-motion'
import { api, useArenaState } from '../api'
import { TEAMS, TEAM_LIST } from '../teams'
import type { Supporter, TeamId } from '../types'
import Header from '../components/Header'
import TeamCard from '../components/TeamCard'
import Commentary from '../components/Commentary'
import QRPanel from '../components/QRPanel'
import Challenge from '../components/Challenge'
import HostControls from '../components/HostControls'
import WinnerOverlay from '../components/WinnerOverlay'
import { setCommentaryAudio, unlockAudio } from '../lib/commentary'
import CommentaryAudio from '../components/CommentaryAudio'

export default function Arena() {
  const { state, offline } = useArenaState(1000)
  const audioOn = state?.audioEnabled ?? false
  useEffect(() => setCommentaryAudio(audioOn), [audioOn])

  const byTeam = useMemo(() => {
    const m: Record<TeamId, Supporter[]> = { blitz: [], oracle: [], maverick: [] }
    for (const s of state?.supporters ?? []) m[s.team]?.push(s)
    return m
  }, [state?.supporters])

  if (!state) {
    return (
      <div className="arena" style={{ placeItems: 'center' }}>
        <div className="grid-bg" />
        <div className="eyebrow" style={{ gridRow: 2 }}>
          {offline ? 'Waiting for arena server…' : 'Connecting…'}
        </div>
      </div>
    )
  }

  const phase = state.racePhase
  const winner = state.winner ? TEAMS[state.winner] : null
  const lobby = phase === 'lobby'

  return (
    <div className="arena" onClick={unlockAudio}>
      <div className="grid-bg" />
      {offline && <div className="offline">RECONNECTING…</div>}
      <CommentaryAudio state={state} />

      <Header
        phase={phase}
        raceStartedAt={state.raceStartedAt}
        audioOn={audioOn}
        voxtral={state.voice.tts}
        onToggleAudio={() => {
          // Flip locally first so the click counts as the user gesture that unlocks audio playback.
          setCommentaryAudio(!audioOn)
          void api.audio(!audioOn)
        }}
      />

      <section className="cards">
        {TEAM_LIST.map((t) => (
          <TeamCard
            key={t.id}
            team={t}
            supporters={byTeam[t.id]}
            events={state.events[t.id] ?? []}
            phase={phase}
            dimmed={!!winner && winner.id !== t.id}
            winner={!!winner && winner.id === t.id}
          />
        ))}
      </section>

      <section className={`bottom ${lobby ? 'lobby' : ''}`}>
        {lobby ? (
          <>
            <Challenge />
            <QRPanel url={state.publicUrl} locked={state.picksLocked} compact={false} />
          </>
        ) : (
          <>
            <Commentary entries={state.commentary} voice={state.voice} />
            <QRPanel url={state.publicUrl} locked={state.picksLocked} compact />
          </>
        )}
      </section>

      <AnimatePresence>{winner && <WinnerOverlay key={winner.id} team={winner} supporters={byTeam[winner.id]} />}</AnimatePresence>

      <HostControls state={state} />
    </div>
  )
}
