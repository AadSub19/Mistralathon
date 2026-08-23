/**
 * Commentary bus.
 *
 * `publishCommentary(text)` is THE integration point. Today a deterministic
 * formatter (see `systemCommentaryFromEvents`) calls it. Later, a Mistral /
 * Voxtral producer can call the same function (directly, or via
 * POST /api/commentary) without touching the UI.
 */
import type { CommentaryEntry, RaceEvent, RacePhase, TeamId } from './types.js'
import { TEAM_IDS } from './types.js'

const MAX_ENTRIES = 30
let nextId = 1
const entries: CommentaryEntry[] = []

export function publishCommentary(text: string, source: CommentaryEntry['source'] = 'system'): CommentaryEntry {
  const clean = text.trim().slice(0, 280)
  const entry: CommentaryEntry = { id: nextId++, text: clean, ts: Date.now(), source }
  entries.push(entry)
  if (entries.length > MAX_ENTRIES) entries.splice(0, entries.length - MAX_ENTRIES)
  return entry
}

export function getCommentary(): CommentaryEntry[] {
  return entries
}

export function markAudioReady(id: number) {
  const e = entries.find((x) => x.id === id)
  if (e) e.audio = true
}

export function recentCommentaryTexts(n = 3): string[] {
  return entries.slice(-n).map((e) => e.text)
}

export function resetCommentary() {
  entries.length = 0
}

// ---------------------------------------------------------------------------
// Deterministic system commentary derived from observable events only.
// ---------------------------------------------------------------------------

const NAME: Record<TeamId, string> = { blitz: 'Blitz', oracle: 'Oracle', maverick: 'Maverick' }

/** Past-tense headline for the newest event. Observable actions only. */
function headline(e: RaceEvent): string | null {
  const a = e.action
  const t = NAME[e.team]
  const map: Record<string, string> = {
    architect_started: `${t} is drawing up its approach`,
    plan_created: `${t} has a blueprint`,
    developer_started: `${t} has started assembling its Pizza Agent`,
    agent_spec_created: `${t}'s agent is taking shape`,
    qa_started: `${t} is stress-testing its agent`,
    qa_issue_found: `${t} found a problem and is working through it`,
    qa_fix_applied: `${t} patched its agent`,
    agent_ready: `${t}'s Pizza Agent is cleared to race`,
    error: `${t} hit turbulence`,
    agent_launched: `${t} is off the line`,
    navigate: `${t} just opened a new page`,
    search: `${t} is scanning the ordering options`,
    restaurant_found: `${t} has locked onto a restaurant`,
    option_selected: `${t} has committed to an ordering path`,
    cart_state: `${t} updated its cart`,
    type_into: `${t} is filling in details`,
    checkout_reached: `${t} has entered checkout`,
    total_checked: `${t} is verifying the final total`,
    order_placed: `${t} has placed an order`,
    order_confirmed: `${t}'s order is confirmed — the pizza is coming`,
    redirect: `${t} just changed direction`,
  }
  return map[a] ?? null
}

/** Present-progressive status for "meanwhile" clauses. */
export function statusOf(events: RaceEvent[], team: TeamId): string | null {
  const t = NAME[team]
  for (let i = events.length - 1; i >= 0; i--) {
    const a = events[i].action
    const map: Record<string, string> = {
      order_confirmed: `${t} is already confirmed`,
      order_placed: `${t} has ordered`,
      total_checked: `${t} is checking its total`,
      checkout_reached: `${t} is in checkout`,
      cart_state: `${t} is still building a cart`,
      restaurant_found: `${t} is browsing a menu`,
      option_selected: `${t} is on its chosen path`,
      search: `${t} is still searching`,
      navigate: `${t} is still navigating`,
      agent_launched: `${t} is just getting started`,
      agent_ready: `${t} is ready on the grid`,
      qa_started: `${t} is still testing`,
      developer_started: `${t} is still assembling`,
      architect_started: `${t} is still planning`,
    }
    if (map[a]) return map[a]
  }
  return null
}

const PHASE_LINES: Record<RacePhase, string> = {
  lobby: 'Three Mistral teams are on the grid. Back your team before the lights go out.',
  building: 'The teams have the challenge. Each is building its own Pizza Agent — no two approaches alike.',
  racing: 'Lights out. Three Pizza Agents are live in the real world.',
  winner: 'And that is the chequered flag.',
}

export function phaseCommentary(phase: RacePhase): string {
  return PHASE_LINES[phase]
}

let lastSystemAt = 0
const MIN_GAP_MS = 3500

/**
 * Called with the newest event(s). Produces at most one line every few seconds.
 * Returns true if a line was published.
 */
export function systemCommentaryFromEvents(newest: RaceEvent, all: Record<TeamId, RaceEvent[]>): boolean {
  const now = Date.now()
  if (now - lastSystemAt < MIN_GAP_MS) return false
  const head = headline(newest)
  if (!head) return false
  const others = TEAM_IDS.filter((t) => t !== newest.team)
    .map((t) => statusOf(all[t], t))
    .filter((s): s is string => !!s)
  let text = head
  if (others.length === 2) text += `, while ${others[0]} and ${others[1]}.`
  else if (others.length === 1) text += `, while ${others[0]}.`
  else text += '.'
  publishCommentary(text, 'system')
  lastSystemAt = now
  return true
}
