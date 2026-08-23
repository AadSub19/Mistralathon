import type { TeamId } from './types'

export interface TeamMeta {
  id: TeamId
  index: string
  name: string
  glyph: string
  title: string
  tagline: string
  color: string
  colorSoft: string
  colorInk: string
}

export const TEAMS: Record<TeamId, TeamMeta> = {
  blitz: {
    id: 'blitz',
    index: '01',
    name: 'BLITZ',
    glyph: '⚡',
    title: 'The Instinct',
    tagline: 'Fast decisions. Relentless momentum. No hesitation.',
    color: '#FF6A1A',
    colorSoft: 'rgba(255, 106, 26, 0.16)',
    colorInk: '#1A0A02',
  },
  oracle: {
    id: 'oracle',
    index: '02',
    name: 'ORACLE',
    glyph: '🔮',
    title: 'The Vision',
    tagline: 'Predictive. Calculated. Always thinking beyond the next move.',
    color: '#A9B7FF',
    colorSoft: 'rgba(169, 183, 255, 0.14)',
    colorInk: '#0B0D1F',
  },
  maverick: {
    id: 'maverick',
    index: '03',
    name: 'MAVERICK',
    glyph: '🃏',
    title: 'The Wildcard',
    tagline: 'Unpredictable. Adaptive. Finds routes others never see.',
    color: '#F2C94C',
    colorSoft: 'rgba(242, 201, 76, 0.14)',
    colorInk: '#1C1504',
  },
}

export const TEAM_LIST = [TEAMS.blitz, TEAMS.oracle, TEAMS.maverick]
