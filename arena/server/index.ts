import './env.js'
import express from 'express'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { store, resetStore } from './state.js'
import { TEAM_IDS, type ArenaState, type RacePhase, type TeamId } from './types.js'
import { getAllEvents, getSources, resetMock, setMockPhase, tickMock, eventsFile } from './events.js'
import {
  getCommentary,
  markAudioReady,
  phaseCommentary,
  publishCommentary,
  recentCommentaryTexts,
  resetCommentary,
  statusOf,
  systemCommentaryFromEvents,
} from './commentary.js'
import { generateCommentary, getVoiceInfo, initVoice, synthesizeSpeech, ttsAvailable, voxtralConfigured } from './voxtral.js'
import type { CommentaryEntry, RaceEvent } from './types.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PORT = Number(process.env.PORT ?? 8787)
// Port phones should hit. In dev this is Vite (5173); in prod it's this server.
const PUBLIC_PORT = Number(process.env.ARENA_PUBLIC_PORT ?? PORT)

function lanIp(): string {
  const ifaces = os.networkInterfaces()
  for (const name of Object.keys(ifaces)) {
    for (const i of ifaces[name] ?? []) {
      if (i.family === 'IPv4' && !i.internal) return i.address
    }
  }
  return 'localhost'
}

const PUBLIC_URL = (process.env.PUBLIC_ARENA_URL ?? `http://${lanIp()}:${PUBLIC_PORT}`).replace(/\/$/, '')

const app = express()
app.use(express.json())

// ---- voice: host 🎙 toggle (shared) + Voxtral audio cache --------------------
let audioEnabled = false
const audioCache = new Map<number, Buffer>()
const AUDIO_CACHE_MAX = 40

/** Publish a line and, if the host has 🎙 on and Voxtral is configured, synthesise it. */
function say(text: string, source: CommentaryEntry['source'] = 'system'): CommentaryEntry {
  const entry = publishCommentary(text, source)
  void maybeSynthesize(entry)
  return entry
}

async function maybeSynthesize(entry: CommentaryEntry) {
  if (!audioEnabled || !ttsAvailable()) return
  const buf = await synthesizeSpeech(entry.text)
  if (!buf) return
  audioCache.set(entry.id, buf)
  markAudioReady(entry.id)
  if (audioCache.size > AUDIO_CACHE_MAX) {
    const oldest = Math.min(...audioCache.keys())
    audioCache.delete(oldest)
  }
}

function isTeam(x: unknown): x is TeamId {
  return typeof x === 'string' && (TEAM_IDS as string[]).includes(x)
}
function isPhase(x: unknown): x is RacePhase {
  return x === 'lobby' || x === 'building' || x === 'racing' || x === 'winner'
}

function snapshot(): ArenaState {
  return {
    supporters: store.supporters,
    picksLocked: store.picksLocked,
    racePhase: store.racePhase,
    winner: store.winner,
    raceStartedAt: store.raceStartedAt,
    publicUrl: PUBLIC_URL,
    serverTime: Date.now(),
    eventSources: getSources(),
    events: getAllEvents(),
    commentary: getCommentary(),
    audioEnabled,
    voice: {
      engine: voxtralConfigured() ? 'mistral' : 'system',
      tts: ttsAvailable(),
      voiceName: getVoiceInfo().voiceName,
      chatModel: voxtralConfigured() ? getVoiceInfo().chatModel : null,
      ttsModel: ttsAvailable() ? getVoiceInfo().ttsModel : null,
    },
  }
}

app.get('/api/state', (_req, res) => {
  res.json(snapshot())
})

app.post('/api/support', (req, res) => {
  const { id, name, team } = req.body ?? {}
  if (typeof id !== 'string' || !id || typeof name !== 'string' || !isTeam(team)) {
    return res.status(400).json({ error: 'id, name and team are required' })
  }
  const cleanName = name.trim().replace(/\s+/g, ' ').slice(0, 24)
  if (!cleanName) return res.status(400).json({ error: 'Name is required' })
  const existing = store.supporters.find((s) => s.id === id)
  if (store.picksLocked) {
    if (existing) return res.status(423).json({ error: 'Picks are locked', supporter: existing })
    return res.status(423).json({ error: 'Picks are locked' })
  }
  if (existing) {
    existing.name = cleanName
    if (existing.team !== team) {
      existing.team = team
      existing.ts = Date.now()
    }
    return res.json({ ok: true, supporter: existing, changed: true })
  }
  const supporter = { id, name: cleanName, team, ts: Date.now() }
  store.supporters.push(supporter)
  res.json({ ok: true, supporter })
})

app.get('/api/support/:id', (req, res) => {
  const s = store.supporters.find((x) => x.id === req.params.id)
  res.json({ supporter: s ?? null, picksLocked: store.picksLocked, racePhase: store.racePhase, winner: store.winner })
})

app.post('/api/admin/lock', (req, res) => {
  const locked = req.body?.locked
  store.picksLocked = typeof locked === 'boolean' ? locked : true
  res.json({ ok: true, picksLocked: store.picksLocked })
})

function setPhase(phase: RacePhase) {
  if (store.racePhase === phase) return
  store.racePhase = phase
  if (phase === 'racing' && !store.raceStartedAt) store.raceStartedAt = Date.now()
  if (phase === 'lobby') {
    store.raceStartedAt = null
    store.winner = null
  }
  if (phase !== 'winner') store.winner = null
  setMockPhase(phase)
  say(phaseCommentary(phase), 'system')
}

app.post('/api/admin/phase', (req, res) => {
  const phase = req.body?.phase
  if (!isPhase(phase)) return res.status(400).json({ error: 'invalid phase' })
  setPhase(phase)
  res.json({ ok: true, racePhase: store.racePhase })
})

app.post('/api/admin/winner', (req, res) => {
  const team = req.body?.team
  if (team !== null && !isTeam(team)) return res.status(400).json({ error: 'invalid team' })
  if (team === null) {
    store.winner = null
    if (store.racePhase === 'winner') store.racePhase = 'racing'
    return res.json({ ok: true, winner: null })
  }
  store.winner = team
  store.racePhase = 'winner'
  store.picksLocked = true
  setMockPhase('winner')
  const backers = store.supporters.filter((s) => s.team === team).length
  const name = team.charAt(0).toUpperCase() + team.slice(1)
  say(`${name} wins the Pizza Grand Prix! ${backers} ${backers === 1 ? 'person' : 'people'} in this room called it.`, 'system')
  res.json({ ok: true, winner: team })
})

app.post('/api/admin/reset', (_req, res) => {
  resetStore()
  resetMock()
  resetCommentary()
  audioCache.clear()
  say(phaseCommentary('lobby'), 'system')
  res.json({ ok: true })
})

/** Host 🎙 toggle. Shared server-side so every screen (and TTS spend) follows it. */
app.post('/api/admin/audio', (req, res) => {
  const was = audioEnabled
  audioEnabled = req.body?.enabled === true
  // Instant feedback: voice a mic-check line the moment the host turns audio on.
  if (audioEnabled && !was) {
    const line =
      store.racePhase === 'lobby'
        ? 'Race control is live. Three Mistral teams on the grid — back your team before the lights go out.'
        : store.racePhase === 'building'
          ? 'Race control is live. The teams are building their Pizza Agents as we speak.'
          : store.racePhase === 'racing'
            ? 'Race control is live. Three Pizza Agents are out on track right now.'
            : 'Race control is live.'
    say(line, 'system')
  }
  res.json({ ok: true, audioEnabled, tts: ttsAvailable() })
})

/** Voxtral audio for a commentary line (mp3). 404 until synthesised. */
app.get('/api/commentary/:id/audio', (req, res) => {
  const buf = audioCache.get(Number(req.params.id))
  if (!buf) return res.status(404).end()
  res.setHeader('Content-Type', 'audio/mpeg')
  res.setHeader('Cache-Control', 'private, max-age=600')
  res.send(buf)
})

/** External commentary producers (Mistral / Voxtral) POST here. */
app.post('/api/commentary', (req, res) => {
  const text = req.body?.text
  if (typeof text !== 'string' || !text.trim()) return res.status(400).json({ error: 'text required' })
  res.json({ ok: true, entry: say(text, 'external') })
})

// ---- event → commentary loop -------------------------------------------------
const seenCounts: Record<TeamId, number> = { blitz: 0, oracle: 0, maverick: 0 }
// Skip everything already on disk at boot so old runs don't spam commentary.
for (const [t, evs] of Object.entries(getAllEvents())) seenCounts[t as TeamId] = evs.length

// Mistral commentary: debounce so one line covers a burst of events.
const MISTRAL_MIN_GAP_MS = Number(process.env.COMMENTARY_INTERVAL_MS ?? 7000)
let pendingNewest: RaceEvent | null = null
let lastMistralAt = 0
let mistralInFlight = false

async function mistralCommentary(newest: RaceEvent, all: Record<TeamId, RaceEvent[]>) {
  mistralInFlight = true
  lastMistralAt = Date.now()
  try {
    const supporters = { blitz: 0, oracle: 0, maverick: 0 } as Record<TeamId, number>
    for (const s of store.supporters) supporters[s.team]++
    const text = await generateCommentary({
      phase: store.racePhase,
      elapsedSec: store.raceStartedAt ? Math.floor((Date.now() - store.raceStartedAt) / 1000) : null,
      newest,
      events: all,
      supporters,
      previous: recentCommentaryTexts(3),
      winner: store.winner,
    })
    if (text) {
      const entry = say(text, 'mistral')
      console.log(`  🎙 ${entry.text}`)
    } else {
      systemCommentaryFromEvents(newest, all)
    }
  } catch (e) {
    console.warn('  mistral commentary failed, using race-control fallback:', (e as Error).message)
    systemCommentaryFromEvents(newest, all)
  } finally {
    mistralInFlight = false
  }
}

setInterval(() => {
  tickMock()
  const all = getAllEvents()
  let newest = null as null | RaceEvent
  for (const t of TEAM_IDS) {
    const evs = all[t]
    if (evs.length > seenCounts[t]) {
      newest = evs[evs.length - 1]
      seenCounts[t] = evs.length
    } else if (evs.length < seenCounts[t]) {
      seenCounts[t] = evs.length
    }
  }
  if (!voxtralConfigured()) {
    if (newest) systemCommentaryFromEvents(newest, all)
    return
  }
  if (newest) pendingNewest = newest
  if (pendingNewest && !mistralInFlight && Date.now() - lastMistralAt >= MISTRAL_MIN_GAP_MS) {
    const n = pendingNewest
    pendingNewest = null
    void mistralCommentary(n, all)
  }
}, 700)

// ---- static (production) -----------------------------------------------------
const dist = path.join(__dirname, '..', 'dist')
if (fs.existsSync(dist)) {
  app.use(express.static(dist))
  app.get('*', (_req, res) => res.sendFile(path.join(dist, 'index.html')))
}

publishCommentary(phaseCommentary('lobby'), 'system')

app.listen(PORT, '0.0.0.0', async () => {
  await initVoice()
  const sources = getSources()
  console.log('')
  console.log('  ╔══════════════════════════════════════════════╗')
  console.log('  ║   MISTRALATHON · PIZZA GRAND PRIX · ARENA     ║')
  console.log('  ╚══════════════════════════════════════════════╝')
  console.log('')
  console.log(`  API server      http://localhost:${PORT}`)
  console.log(`  Host screen     ${PUBLIC_URL}/`)
  console.log(`  JOIN (phones)   ${PUBLIC_URL}/join   ◀ scan / open this on phones`)
  console.log('')
  for (const t of TEAM_IDS) console.log(`  events · ${t.padEnd(8)} ${sources[t].padEnd(5)} ${eventsFile(t)}`)
  console.log('')
  if (!process.env.PUBLIC_ARENA_URL) console.log('  (set PUBLIC_ARENA_URL to override the QR destination)')
  console.log('')
  if (voxtralConfigured()) {
    const v = getVoiceInfo()
    console.log(`  commentary      Mistral · ${v.chatModel}`)
    console.log(`  voice           ${ttsAvailable() ? `Voxtral · ${v.ttsModel} · voice "${v.voiceName ?? 'default'}"` : 'disabled (VOXTRAL_TTS=0)'}`)
  } else {
    console.log('  commentary      race-control formatter (set MISTRAL_API_KEY for Mistral + Voxtral)')
  }
  console.log('')
})
