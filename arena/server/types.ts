export type TeamId = 'blitz' | 'oracle' | 'maverick'
export const TEAM_IDS: TeamId[] = ['blitz', 'oracle', 'maverick']
export type RacePhase = 'lobby' | 'building' | 'racing' | 'winner'

export interface Supporter {
  id: string
  name: string
  team: TeamId
  ts: number
}

export interface RaceEvent {
  ts: string
  team: TeamId
  phase: string
  actor: string
  action: string
  detail: string
}

export interface CommentaryEntry {
  id: number
  text: string
  ts: number
  source: 'system' | 'external' | 'mistral'
  /** true once Voxtral audio for this line is ready at GET /api/commentary/:id/audio */
  audio?: boolean
}

export interface ArenaState {
  supporters: Supporter[]
  picksLocked: boolean
  racePhase: RacePhase
  winner: TeamId | null
  raceStartedAt: number | null
  publicUrl: string
  serverTime: number
  eventSources: Record<TeamId, 'file' | 'mock' | 'none'>
  events: Record<TeamId, RaceEvent[]>
  commentary: CommentaryEntry[]
  /** Host 🎙 toggle — shared so every screen follows it. */
  audioEnabled: boolean
  voice: {
    engine: 'mistral' | 'system'
    tts: boolean
    voiceName: string | null
    chatModel: string | null
    ttsModel: string | null
  }
}
