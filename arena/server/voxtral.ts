/**
 * Mistral-powered race control.
 *
 *   generateCommentary()  → mistral chat completions writes one line of play-by-play
 *                           from OBSERVABLE events only (no reasoning is ever passed in).
 *   synthesizeSpeech()    → Voxtral TTS (POST /v1/audio/speech) turns that line into mp3.
 *
 * Both are optional: with no MISTRAL_API_KEY the arena falls back to the
 * deterministic formatter in commentary.ts and browser TTS on the client.
 */
import type { RaceEvent, RacePhase, TeamId } from './types.js'

const API = (process.env.MISTRAL_API_BASE ?? 'https://api.mistral.ai').replace(/\/$/, '')
const KEY = process.env.MISTRAL_API_KEY ?? ''
const CHAT_MODEL = process.env.MISTRAL_COMMENTARY_MODEL ?? 'mistral-small-latest'
const TTS_MODEL = process.env.VOXTRAL_TTS_MODEL ?? 'voxtral-mini-tts-2603'
const TTS_DISABLED = process.env.VOXTRAL_TTS === '0'

let voiceId: string | null = process.env.VOXTRAL_VOICE_ID ?? null
let voiceName: string | null = null
let ttsHealthy = !TTS_DISABLED
let chatHealthy = true

/** Key present AND the chat endpoint hasn't hard-failed (401/403/404). */
export function voxtralConfigured() {
  return KEY.length > 0 && chatHealthy
}
export function ttsAvailable() {
  return voxtralConfigured() && ttsHealthy
}
export function getVoiceInfo() {
  return { voiceId, voiceName, chatModel: CHAT_MODEL, ttsModel: TTS_MODEL }
}

async function mistral<T>(path: string, init: RequestInit, timeoutMs = 20000): Promise<T> {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(`${API}${path}`, {
      ...init,
      signal: ctrl.signal,
      headers: { Authorization: `Bearer ${KEY}`, 'Content-Type': 'application/json', ...(init.headers ?? {}) },
    })
    if (!res.ok) {
      const body = await res.text().catch(() => '')
      throw new Error(`${res.status} ${res.statusText} ${body.slice(0, 200)}`)
    }
    return (await res.json()) as T
  } finally {
    clearTimeout(t)
  }
}

/** Pick a preset voice once at boot (unless VOXTRAL_VOICE_ID is set). */
export async function initVoice(): Promise<void> {
  if (!voxtralConfigured() || TTS_DISABLED) return
  try {
    const data = await mistral<{ items?: Array<{ id: string; name?: string; gender?: string | null; languages?: string[]; tags?: string[] | null }> }>(
      '/v1/audio/voices?type=preset&limit=50',
      { method: 'GET' },
      10000,
    )
    const items = data.items ?? []
    if (voiceId) {
      voiceName = items.find((v) => v.id === voiceId)?.name ?? voiceId
      return
    }
    const english = items.filter((v) => !v.languages?.length || v.languages.some((l) => /^en/i.test(l)))
    const pool = english.length ? english : items
    const wanted = process.env.VOXTRAL_VOICE_NAME?.toLowerCase()
    const byName = wanted ? pool.find((v) => v.name?.toLowerCase() === wanted) ?? pool.find((v) => v.name?.toLowerCase().includes(wanted)) : undefined
    const UPBEAT = /(excited|energetic|enthusiast|happy|cheerful|upbeat|confident|announcer|sport|hype|dynamic|bright|joyful)/i
    const AVOID = /(sad|whisper|sleepy|calm|tired|bored|angry|cry|soft|gentle|neutral)/i
    const DEFAULTS = ['oliver - excited', 'paul - confident', 'paul - excited', 'oliver - confident']
    const fromDefaults = DEFAULTS.map((n) => pool.find((v) => v.name?.toLowerCase() === n)).find(Boolean)
    const upbeat = fromDefaults ?? pool.find((v) => UPBEAT.test(`${v.name} ${(v.tags ?? []).join(' ')}`))
    const notSad = pool.find((v) => !AVOID.test(`${v.name} ${(v.tags ?? []).join(' ')}`))
    const pick = byName ?? upbeat ?? notSad ?? pool[0]
    if (pick) {
      voiceId = pick.id
      voiceName = pick.name ?? pick.id
    }
  } catch (e) {
    console.warn('  voxtral: could not list voices —', (e as Error).message)
  }
}

// ---------------------------------------------------------------------------
// Commentary text
// ---------------------------------------------------------------------------

const TEAM_NAME: Record<TeamId, string> = { blitz: 'Blitz', oracle: 'Oracle', maverick: 'Maverick' }

/** Human labels for the prompt. Never role names, never raw identifiers. */
const LABEL: Record<string, string> = {
  architect_started: 'started designing its agent',
  plan_created: 'finished its blueprint',
  architect_completed: 'locked in its approach',
  developer_started: 'started assembling its agent',
  agent_spec_created: 'assembled its agent',
  developer_completed: 'finished assembly',
  qa_started: 'started stress-testing its agent',
  test_run: 'ran checks',
  qa_issue_found: 'found a problem in its agent',
  qa_fix_applied: 'patched its agent',
  agent_ready: 'declared its agent ready to race',
  qa_completed: 'finished testing',
  vibe_started: 'opened a new Mistral session',
  vibe_completed: 'closed a Mistral session',
  error: 'hit an error',
  agent_launched: 'launched its Pizza Agent',
  search: 'is searching ordering options',
  navigate: 'opened',
  visible_page_text: 'is reading the page',
  screenshot: 'captured the page',
  click: 'selected an option',
  type_into: 'is entering details',
  restaurant_found: 'found a restaurant',
  option_selected: 'picked an ordering path',
  redirect: 'changed direction',
  cart_state: 'updated its cart',
  checkout_reached: 'reached checkout',
  total_checked: 'is checking the final total',
  order_placed: 'placed an order',
  order_confirmed: 'got its order confirmed',
}
const SKIP = new Set(['stage_started', 'stage_completed', 'file_created', 'current_url'])

/** Sanitise an event for the prompt: clean label + short, path-free detail. Observable only. */
function eventLine(e: RaceEvent): string | null {
  if (SKIP.has(e.action)) return null
  const label = LABEL[e.action] ?? e.action.replace(/[_-]+/g, ' ')
  let d = ''
  if (e.action === 'navigate') {
    try {
      d = new URL((e.detail ?? '').trim()).hostname.replace(/^www\./, '')
    } catch {
      d = 'a page'
    }
  } else if (e.action === 'cart_state' || e.action === 'total_checked' || e.action === 'order_confirmed') {
    const m = (e.detail ?? '').match(/\$\s?\d+(?:\.\d{2})?|ETA[^·]*$/i)
    d = m?.[0]?.trim() ?? ''
  } else if (e.action === 'vibe_completed' && /exit code [1-9]/.test(e.detail ?? '')) {
    d = 'with an error'
  }
  return d ? `${label} ${d}` : label
}

/** Output guard: no role names, no raw identifiers. Fails closed (→ deterministic fallback). */
const FORBIDDEN = /\b(architect|developer|qa|q\.a\.|cli|exit code)\b|\w+_\w+/i

export interface CommentaryContext {
  phase: RacePhase
  elapsedSec: number | null
  newest: RaceEvent
  events: Record<TeamId, RaceEvent[]>
  supporters: Record<TeamId, number>
  previous: string[]
  winner: TeamId | null
}

const SYSTEM = `You are the live race-control commentator for the MISTRALATHON PIZZA GRAND PRIX: three autonomous AI agents (teams Blitz, Oracle and Maverick) racing to get a real pepperoni + jalapeño pizza delivered for under $35. It is a Formula 1-style broadcast for AI — sharp, energetic, premium, never cheesy.

Rules:
- Write exactly ONE sentence of commentary, 12–28 words. No preamble, no quotes, no emojis, no hashtags.
- Describe only the OBSERVABLE actions in the event log. Never speculate about what an agent is thinking, planning, or why. Never invent prices, restaurants, or events not in the log.
- Use team names (Blitz, Oracle, Maverick). The newest event is the headline; contrast with where the others are.
- Before the race the teams are building their agents (designing → assembling → testing → ready). During the race the agents are operating real ordering websites.
- Never use the words Architect, Developer, QA, CLI, or any technical identifiers. Talk like a broadcaster, not an engineer.
- Vary your phrasing from the previous lines. Present tense. Energy like the final lap.`

export async function generateCommentary(ctx: CommentaryContext): Promise<string | null> {
  if (!voxtralConfigured()) return null
  try {
    return await generateCommentaryInner(ctx)
  } catch (e) {
    const msg = (e as Error).message
    if (/^(401|403|404)/.test(msg)) {
      chatHealthy = false
      ttsHealthy = false
      console.warn('  mistral: disabling Mistral commentary + Voxtral for this run —', msg)
    }
    throw e
  }
}

async function generateCommentaryInner(ctx: CommentaryContext): Promise<string | null> {
  const teams = (Object.keys(ctx.events) as TeamId[]).map((t) => {
    const recent = ctx.events[t].slice(-8).map(eventLine).filter((x): x is string => !!x).slice(-5)
    return `${TEAM_NAME[t]} (${ctx.supporters[t]} backers), most recent last: ${recent.length ? recent.join(' → ') : 'nothing yet'}`
  })
  const user = [
    `Race phase: ${ctx.phase}${ctx.elapsedSec != null ? ` · elapsed ${Math.floor(ctx.elapsedSec / 60)}m${ctx.elapsedSec % 60}s` : ''}`,
    ctx.winner ? `Winner declared: ${TEAM_NAME[ctx.winner]}` : '',
    `NEWEST: ${TEAM_NAME[ctx.newest.team]} ${eventLine(ctx.newest) ?? 'made a move'}`,
    ...teams,
    ctx.previous.length ? `Previous commentary (do not repeat): ${ctx.previous.slice(-3).join(' / ')}` : '',
    'Write the next line.',
  ]
    .filter(Boolean)
    .join('\n')

  const data = await mistral<{ choices?: Array<{ message?: { content?: string | Array<{ type: string; text?: string }> } }> }>(
    '/v1/chat/completions',
    {
      method: 'POST',
      body: JSON.stringify({
        model: CHAT_MODEL,
        temperature: 0.8,
        max_tokens: 80,
        messages: [
          { role: 'system', content: SYSTEM },
          { role: 'user', content: user },
        ],
      }),
    },
  )
  const raw = data.choices?.[0]?.message?.content
  const text = (typeof raw === 'string' ? raw : raw?.map((p) => p.text ?? '').join('') ?? '').trim()
  if (!text) return null
  const line = text.replace(/^["“]+|["”]+$/g, '').split('\n')[0].slice(0, 240)
  if (FORBIDDEN.test(line)) {
    console.warn('  mistral: dropped a line that leaked internals →', line)
    return null
  }
  return line
}

// ---------------------------------------------------------------------------
// Voxtral TTS
// ---------------------------------------------------------------------------

export async function synthesizeSpeech(text: string): Promise<Buffer | null> {
  if (!ttsAvailable()) return null
  try {
    const data = await mistral<{ audio_data?: string }>(
      '/v1/audio/speech',
      {
        method: 'POST',
        body: JSON.stringify({
          model: TTS_MODEL,
          input: text,
          ...(voiceId ? { voice_id: voiceId } : {}),
          response_format: 'mp3',
        }),
      },
      30000,
    )
    if (!data.audio_data) return null
    return Buffer.from(data.audio_data, 'base64')
  } catch (e) {
    const msg = (e as Error).message
    console.warn('  voxtral tts:', msg)
    // Hard auth/model errors → stop retrying every line; transient ones keep trying.
    if (/^(401|403|404|422)/.test(msg)) ttsHealthy = false
    return null
  }
}
