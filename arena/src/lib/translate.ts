/**
 * Translate raw observable events into human-readable race activity.
 * Never surfaces reasoning — only actions. Never reveals build-role names.
 */
import type { RaceEvent } from '../types'

export interface Activity {
  label: string
  detail?: string
  kind: 'build' | 'race' | 'milestone' | 'warn'
  key: string
}

const NOISE = new Set(['stage_started', 'stage_completed', 'file_created', 'current_url'])

const LABELS: Record<string, [string, Activity['kind']]> = {
  // build
  architect_started: ['Drawing up the approach', 'build'],
  vibe_started: ['Mistral session started', 'build'],
  vibe_completed: ['Mistral session finished', 'build'],
  plan_created: ['Blueprint ready', 'milestone'],
  architect_completed: ['Approach locked in', 'build'],
  developer_started: ['Assembling the Pizza Agent', 'build'],
  agent_spec_created: ['Agent assembled', 'milestone'],
  developer_completed: ['Assembly complete', 'build'],
  qa_started: ['Stress-testing the agent', 'build'],
  test_run: ['Running checks', 'build'],
  qa_issue_found: ['Issue detected', 'warn'],
  qa_fix_applied: ['Fix applied', 'build'],
  agent_ready: ['Agent ready to race', 'milestone'],
  qa_completed: ['Testing complete', 'build'],
  error: ['Hit a snag', 'warn'],
  // race
  agent_launched: ['Agent launched', 'milestone'],
  search: ['Searching ordering options', 'race'],
  navigate: ['Opened a page', 'race'],
  visible_page_text: ['Reading the page', 'race'],
  screenshot: ['Captured the page', 'race'],
  click: ['Selected an option', 'race'],
  type_into: ['Entering details', 'race'],
  restaurant_found: ['Restaurant discovered', 'milestone'],
  option_selected: ['Ordering path selected', 'milestone'],
  redirect: ['Changed direction', 'race'],
  cart_state: ['Cart updated', 'race'],
  checkout_reached: ['Checkout reached', 'milestone'],
  total_checked: ['Checking final total', 'race'],
  order_placed: ['Order placed', 'milestone'],
  order_confirmed: ['Order confirmed', 'milestone'],
}

function hostOf(url: string): string | null {
  try {
    return new URL(url.trim()).hostname.replace(/^www\./, '')
  } catch {
    return null
  }
}

export function isNoise(e: RaceEvent) {
  return NOISE.has(e.action)
}

export function describe(e: RaceEvent, i: number): Activity {
  const key = `${e.ts}-${i}-${e.action}`
  const found = LABELS[e.action]
  if (e.action === 'navigate') {
    const host = hostOf(e.detail)
    return { label: host ? `Opened ${host}` : 'Opened a page', kind: 'race', key }
  }
  if (e.action === 'cart_state' && e.detail && e.detail.length <= 40 && !/[{}"]/.test(e.detail)) {
    return { label: 'Cart updated', detail: e.detail, kind: 'race', key }
  }
  if (e.action === 'total_checked' && /\$\s?\d/.test(e.detail)) {
    const m = e.detail.match(/\$\s?\d+(?:\.\d{2})?/)
    return { label: 'Checking final total', detail: m?.[0], kind: 'race', key }
  }
  if (e.action === 'order_confirmed' && /ETA/i.test(e.detail)) {
    const m = e.detail.match(/ETA[^·]*$/i)
    return { label: 'Order confirmed', detail: m?.[0]?.trim(), kind: 'milestone', key }
  }
  if (found) return { label: found[0], kind: found[1], key }
  // Unknown action: humanise the snake_case name only. Never dump detail.
  const label = e.action.replace(/[_-]+/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
  return { label, kind: e.phase === 'execution' ? 'race' : 'build', key }
}

export function recentActivity(events: RaceEvent[], n = 4): Activity[] {
  const out: Activity[] = []
  for (let i = events.length - 1; i >= 0 && out.length < n; i--) {
    const e = events[i]
    if (isNoise(e)) continue
    out.push(describe(e, i))
  }
  return out.reverse()
}

/** Observable progress: 0–6 pixel blocks lit, derived from milestones only. */
const BUILD_STAGES = ['architect_started', 'plan_created', 'developer_started', 'agent_spec_created', 'qa_started', 'agent_ready']
const RACE_STAGES = ['agent_launched', 'restaurant_found|option_selected|navigate', 'cart_state', 'checkout_reached', 'order_placed', 'order_confirmed']

export function progress(events: RaceEvent[], mode: 'build' | 'race'): number {
  const stages = mode === 'build' ? BUILD_STAGES : RACE_STAGES
  const seen = new Set(events.map((e) => e.action))
  let lit = 0
  for (let i = 0; i < stages.length; i++) {
    if (stages[i].split('|').some((a) => seen.has(a))) lit = i + 1
  }
  return lit
}

export function hasAction(events: RaceEvent[], action: string) {
  return events.some((e) => e.action === action)
}
