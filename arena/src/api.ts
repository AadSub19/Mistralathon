import { useEffect, useRef, useState } from 'react'
import type { ArenaState, RacePhase, TeamId } from './types'

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...init })
  const body = (await res.json().catch(() => ({}))) as T & { error?: string }
  if (!res.ok) throw Object.assign(new Error(body.error ?? res.statusText), { status: res.status, body })
  return body
}

/** Poll /api/state every `ms`. Simple and reliable over any network. */
export function useArenaState(ms = 1000) {
  const [state, setState] = useState<ArenaState | null>(null)
  const [offline, setOffline] = useState(false)
  const timer = useRef<number | null>(null)
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const s = await json<ArenaState>('/api/state')
        if (alive) {
          setState(s)
          setOffline(false)
        }
      } catch {
        if (alive) setOffline(true)
      }
      if (alive) timer.current = window.setTimeout(tick, ms)
    }
    tick()
    return () => {
      alive = false
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [ms])
  return { state, offline }
}

export const api = {
  support: (id: string, name: string, team: TeamId) =>
    json<{ ok: boolean; supporter: { team: TeamId; name: string } }>('/api/support', {
      method: 'POST',
      body: JSON.stringify({ id, name, team }),
    }),
  mySupport: (id: string) =>
    json<{ supporter: { team: TeamId; name: string } | null; picksLocked: boolean; racePhase: RacePhase; winner: TeamId | null }>(
      `/api/support/${encodeURIComponent(id)}`,
    ),
  lock: (locked: boolean) => json('/api/admin/lock', { method: 'POST', body: JSON.stringify({ locked }) }),
  phase: (phase: RacePhase) => json('/api/admin/phase', { method: 'POST', body: JSON.stringify({ phase }) }),
  winner: (team: TeamId | null) => json('/api/admin/winner', { method: 'POST', body: JSON.stringify({ team }) }),
  reset: () => json('/api/admin/reset', { method: 'POST' }),
  audio: (enabled: boolean) => json('/api/admin/audio', { method: 'POST', body: JSON.stringify({ enabled }) }),
  commentary: (text: string) => json('/api/commentary', { method: 'POST', body: JSON.stringify({ text }) }),
}

/** Stable per-browser participant id. */
export function participantId(): string {
  const KEY = 'mistralathon_pid'
  try {
    let id = localStorage.getItem(KEY)
    if (!id) {
      id = (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36))
      localStorage.setItem(KEY, id)
    }
    return id
  } catch {
    return 'anon-' + Math.random().toString(36).slice(2)
  }
}
