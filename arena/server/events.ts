/**
 * Event source.
 *
 * Default: read runs/<team>/events.jsonl (written by the orchestrator / execution
 * layer). Per team, if that file does not exist (or ARENA_MOCK=1), a mock
 * generator produces plausible *observable* events so the UI can be exercised.
 * ARENA_MOCK=0 disables mock entirely.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { RaceEvent, RacePhase, TeamId } from './types.js'
import { TEAM_IDS } from './types.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '..', '..')
const RUNS_DIR = process.env.ARENA_RUNS_DIR ?? path.join(REPO_ROOT, 'runs')
const MOCK_MODE = process.env.ARENA_MOCK // '1' | '0' | undefined

const MAX_EVENTS_PER_TEAM = 120

type Cache = { mtimeMs: number; size: number; events: RaceEvent[] }
const fileCache: Partial<Record<TeamId, Cache>> = {}
const mockEvents: Record<TeamId, RaceEvent[]> = { blitz: [], oracle: [], maverick: [] }

export function eventsFile(team: TeamId) {
  return path.join(RUNS_DIR, team, 'events.jsonl')
}

function hasFile(team: TeamId) {
  try {
    return fs.statSync(eventsFile(team)).isFile()
  } catch {
    return false
  }
}

export function sourceFor(team: TeamId): 'file' | 'mock' | 'none' {
  if (MOCK_MODE === '1') return 'mock'
  if (hasFile(team)) return 'file'
  if (MOCK_MODE === '0') return 'none'
  return 'mock'
}

function normalise(raw: Record<string, unknown>, team: TeamId): RaceEvent | null {
  const action = typeof raw.action === 'string' ? raw.action : null
  if (!action) return null
  const ts = (raw.ts ?? raw.timestamp ?? new Date().toISOString()) as string
  return {
    ts: String(ts),
    team: (String(raw.team ?? team).toLowerCase() as TeamId) || team,
    phase: String(raw.phase ?? ''),
    actor: String(raw.actor ?? ''),
    action,
    detail: typeof raw.detail === 'string' ? raw.detail : raw.detail ? JSON.stringify(raw.detail) : '',
  }
}

function readFileEvents(team: TeamId): RaceEvent[] {
  const file = eventsFile(team)
  let st: fs.Stats
  try {
    st = fs.statSync(file)
  } catch {
    return []
  }
  const cached = fileCache[team]
  if (cached && cached.mtimeMs === st.mtimeMs && cached.size === st.size) return cached.events
  const events: RaceEvent[] = []
  const text = fs.readFileSync(file, 'utf8')
  for (const line of text.split('\n')) {
    const l = line.trim()
    if (!l) continue
    try {
      const ev = normalise(JSON.parse(l), team)
      if (ev) events.push(ev)
    } catch {
      /* skip malformed line */
    }
  }
  const trimmed = events.slice(-MAX_EVENTS_PER_TEAM)
  fileCache[team] = { mtimeMs: st.mtimeMs, size: st.size, events: trimmed }
  return trimmed
}

export function getAllEvents(): Record<TeamId, RaceEvent[]> {
  const out = {} as Record<TeamId, RaceEvent[]>
  for (const t of TEAM_IDS) {
    const src = sourceFor(t)
    out[t] = src === 'file' ? readFileEvents(t) : src === 'mock' ? mockEvents[t] : []
  }
  return out
}

export function getSources(): Record<TeamId, 'file' | 'mock' | 'none'> {
  const out = {} as Record<TeamId, 'file' | 'mock' | 'none'>
  for (const t of TEAM_IDS) out[t] = sourceFor(t)
  return out
}

// ---------------------------------------------------------------------------
// Mock generator — observable actions only, no reasoning. Each team has a
// different *tempo*, not a different strategy.
// ---------------------------------------------------------------------------

type Step = [phase: string, actor: string, action: string, detail: string]

const BUILD_SCRIPT: Step[] = [
  ['architect', 'architect', 'architect_started', 'Architect phase began for team'],
  ['architect', 'architect', 'vibe_started', 'Vibe CLI process started'],
  ['architect', 'architect', 'vibe_completed', 'Vibe CLI process completed with exit code 0'],
  ['architect', 'architect', 'plan_created', 'Plan created at runs/{team}/PLAN.md'],
  ['architect', 'architect', 'architect_completed', 'Architect phase completed'],
  ['developer', 'developer', 'developer_started', 'Developer phase began'],
  ['developer', 'developer', 'vibe_started', 'Vibe CLI process started'],
  ['developer', 'developer', 'vibe_completed', 'Vibe CLI process completed with exit code 0'],
  ['developer', 'developer', 'agent_spec_created', 'Agent specification created at runs/{team}/pizza-agent/agent_spec.json'],
  ['developer', 'developer', 'developer_completed', 'Developer phase completed'],
  ['qa', 'qa', 'qa_started', 'QA phase began'],
  ['qa', 'qa', 'vibe_started', 'Vibe CLI process started'],
  ['qa', 'qa', 'test_run', "Test 'constraints' result: pass"],
  ['qa', 'qa', 'vibe_completed', 'Vibe CLI process completed with exit code 0'],
  ['qa', 'qa', 'agent_ready', 'Agent is ready for execution'],
  ['qa', 'qa', 'qa_completed', 'QA phase completed'],
]

const RACE_SCRIPTS: Record<TeamId, Step[]> = {
  blitz: [
    ['execution', 'agent', 'agent_launched', 'Pizza Agent launched'],
    ['execution', 'agent', 'search', 'Searching ordering options'],
    ['execution', 'agent', 'navigate', 'https://www.dominos.com/'],
    ['execution', 'agent', 'visible_page_text', 'Reading page'],
    ['execution', 'agent', 'restaurant_found', 'Restaurant discovered'],
    ['execution', 'agent', 'click', 'Build Your Own Pizza'],
    ['execution', 'agent', 'cart_state', '1 item · $18.49'],
    ['execution', 'agent', 'click', 'Checkout'],
    ['execution', 'agent', 'checkout_reached', 'Checkout reached'],
    ['execution', 'agent', 'type_into', 'delivery address'],
    ['execution', 'agent', 'total_checked', 'Delivered total $27.80'],
    ['execution', 'agent', 'order_placed', 'Order placed'],
    ['execution', 'agent', 'order_confirmed', 'Order confirmed · ETA 28 min'],
  ],
  oracle: [
    ['execution', 'agent', 'agent_launched', 'Pizza Agent launched'],
    ['execution', 'agent', 'search', 'Evaluating available options'],
    ['execution', 'agent', 'navigate', 'https://www.doordash.com/'],
    ['execution', 'agent', 'visible_page_text', 'Reading page'],
    ['execution', 'agent', 'navigate', 'https://www.ubereats.com/'],
    ['execution', 'agent', 'visible_page_text', 'Reading page'],
    ['execution', 'agent', 'option_selected', 'Ordering path selected'],
    ['execution', 'agent', 'restaurant_found', 'Restaurant discovered'],
    ['execution', 'agent', 'cart_state', '1 item · $21.00'],
    ['execution', 'agent', 'checkout_reached', 'Checkout reached'],
    ['execution', 'agent', 'total_checked', 'Delivered total $31.15'],
    ['execution', 'agent', 'order_placed', 'Order placed'],
    ['execution', 'agent', 'order_confirmed', 'Order confirmed · ETA 24 min'],
  ],
  maverick: [
    ['execution', 'agent', 'agent_launched', 'Pizza Agent launched'],
    ['execution', 'agent', 'navigate', 'https://www.google.com/maps'],
    ['execution', 'agent', 'search', 'Exploring alternative path'],
    ['execution', 'agent', 'navigate', 'https://slicelife.com/'],
    ['execution', 'agent', 'restaurant_found', 'New option discovered'],
    ['execution', 'agent', 'redirect', 'Changed direction'],
    ['execution', 'agent', 'navigate', 'https://www.grubhub.com/'],
    ['execution', 'agent', 'cart_state', '1 item · $16.75'],
    ['execution', 'agent', 'cart_state', '1 item · $19.25'],
    ['execution', 'agent', 'checkout_reached', 'Checkout reached'],
    ['execution', 'agent', 'total_checked', 'Delivered total $29.40'],
    ['execution', 'agent', 'order_placed', 'Order placed'],
    ['execution', 'agent', 'order_confirmed', 'Order confirmed · ETA 33 min'],
  ],
}

/** Tempo per team: [minMs, maxMs] between events. */
const TEMPO: Record<TeamId, [number, number]> = {
  blitz: [1800, 3200],
  oracle: [3000, 4500],
  maverick: [1200, 6000],
}

type MockRun = { phase: RacePhase; idx: number; nextAt: number }
const mockRuns: Partial<Record<TeamId, MockRun>> = {}
let currentPhase: RacePhase = 'lobby'

function rand(min: number, max: number) {
  return min + Math.random() * (max - min)
}

export function setMockPhase(phase: RacePhase) {
  if (phase === currentPhase) return
  currentPhase = phase
  if (phase === 'building' || phase === 'racing') {
    for (const t of TEAM_IDS) {
      if (sourceFor(t) !== 'mock') continue
      mockRuns[t] = { phase, idx: 0, nextAt: Date.now() + rand(500, 2500) }
    }
  }
}

export function resetMock() {
  for (const t of TEAM_IDS) {
    mockEvents[t] = []
    delete mockRuns[t]
  }
  currentPhase = 'lobby'
}

/** Advance mock generators. Returns newly created events (for commentary). */
export function tickMock(): RaceEvent[] {
  const created: RaceEvent[] = []
  const now = Date.now()
  for (const t of TEAM_IDS) {
    const run = mockRuns[t]
    if (!run || sourceFor(t) !== 'mock') continue
    const script = run.phase === 'building' ? BUILD_SCRIPT : RACE_SCRIPTS[t]
    if (run.idx >= script.length || now < run.nextAt) continue
    const [phase, actor, action, detail] = script[run.idx]
    const ev: RaceEvent = {
      ts: new Date(now).toISOString(),
      team: t,
      phase,
      actor,
      action,
      detail: detail.replace('{team}', t),
    }
    mockEvents[t].push(ev)
    if (mockEvents[t].length > MAX_EVENTS_PER_TEAM) mockEvents[t].shift()
    created.push(ev)
    run.idx += 1
    const [lo, hi] = TEMPO[t]
    run.nextAt = now + rand(lo, hi)
  }
  return created
}
