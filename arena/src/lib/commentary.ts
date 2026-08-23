/**
 * Client-side commentary audio.
 *
 * Text is produced server-side (server/commentary.ts → publishCommentary, fed by
 * Mistral when MISTRAL_API_KEY is set, else a deterministic formatter).
 *
 * Audio, when the host 🎙 toggle is on:
 *   1. Voxtral — the server synthesises each line; we stream GET /api/commentary/:id/audio.
 *   2. Fallback — browser speechSynthesis if Voxtral isn't configured.
 *
 * Lines play sequentially; if several arrive while one is playing, only the
 * newest pending line is kept so the broadcast never lags the race.
 */
import { api } from '../api'
import type { CommentaryEntry } from '../types'

let enabled = false
let current: HTMLAudioElement | null = null
let pending: CommentaryEntry | null = null
let playing = false

export type AudioStatus = 'off' | 'idle' | 'playing' | 'blocked'
let status: AudioStatus = 'off'
const listeners = new Set<(s: AudioStatus) => void>()
function setStatus(s: AudioStatus) {
  status = s
  listeners.forEach((l) => l(s))
}
export function getAudioStatus() {
  return status
}
export function onAudioStatus(l: (s: AudioStatus) => void) {
  listeners.add(l)
  return () => {
    listeners.delete(l)
  }
}

export function setCommentaryAudio(on: boolean) {
  enabled = on
  if (!on) {
    pending = null
    current?.pause()
    current = null
    playing = false
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    setStatus('off')
  } else if (status === 'off') {
    setStatus('idle')
  }
}

/** Call from a click handler: unlocks autoplay and replays the last blocked line. */
export function unlockAudio() {
  if (status !== 'blocked') return
  setStatus('idle')
  if (lastBlocked) {
    seen.delete(lastBlocked.id)
    speakCommentary(lastBlocked, true)
  }
}
let lastBlocked: CommentaryEntry | null = null

export function isCommentaryAudioEnabled() {
  return enabled
}

function browserSpeak(text: string): Promise<void> {
  return new Promise((resolve) => {
    if (!('speechSynthesis' in window)) return resolve()
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.rate = 1.05
    u.pitch = 0.95
    u.onend = () => resolve()
    u.onerror = () => resolve()
    window.speechSynthesis.speak(u)
  })
}

function playUrl(url: string, entry: CommentaryEntry): Promise<void> {
  return new Promise((resolve) => {
    const a = new Audio(url)
    current = a
    a.onended = () => {
      setStatus('idle')
      resolve()
    }
    a.onerror = () => {
      setStatus('idle')
      resolve()
    }
    a.play()
      .then(() => setStatus('playing'))
      .catch((err: DOMException) => {
        if (err?.name === 'NotAllowedError') {
          lastBlocked = entry
          setStatus('blocked')
        }
        resolve()
      })
  })
}

async function drain(useVoxtral: boolean) {
  if (playing) return
  playing = true
  while (pending && enabled) {
    const e = pending
    pending = null
    if (useVoxtral && e.audio) await playUrl(`/api/commentary/${e.id}/audio`, e)
    else if (!useVoxtral) {
      setStatus('playing')
      await browserSpeak(e.text)
      setStatus('idle')
    }
  }
  playing = false
  current = null
}

/** Queue a line for playback. Safe to call repeatedly with the same entry. */
const seen = new Set<number>()
export function speakCommentary(entry: CommentaryEntry, useVoxtral: boolean) {
  if (!enabled) return
  if (useVoxtral && !entry.audio) return // not synthesised yet — caller retries on next poll
  if (seen.has(entry.id)) return
  seen.add(entry.id)
  pending = entry
  void drain(useVoxtral)
}

/** Publish a line from the client (e.g. a manual host announcement). */
export function publishCommentary(text: string) {
  return api.commentary(text)
}
