import { useEffect } from 'react'
import type { ArenaState } from '../types'
import { speakCommentary } from '../lib/commentary'

/**
 * Mounted on the host screen in EVERY phase (the Commentary panel itself is
 * hidden in Lobby). Hands the newest line to the audio queue on each poll; the
 * queue dedupes by id and waits for Voxtral audio to be ready.
 */
export default function CommentaryAudio({ state }: { state: ArenaState }) {
  const latest = state.commentary[state.commentary.length - 1]
  const tts = state.voice.tts
  useEffect(() => {
    if (latest) speakCommentary(latest, tts)
  }, [latest, latest?.audio, tts])
  return null
}
