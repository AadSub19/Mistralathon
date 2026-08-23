import type { RacePhase, Supporter, TeamId } from './types.js'

/** Hackathon-grade in-memory state. No DB. */
export const store = {
  supporters: [] as Supporter[],
  picksLocked: false,
  racePhase: 'lobby' as RacePhase,
  winner: null as TeamId | null,
  raceStartedAt: null as number | null,
}

export function resetStore() {
  store.supporters = []
  store.picksLocked = false
  store.racePhase = 'lobby'
  store.winner = null
  store.raceStartedAt = null
}
