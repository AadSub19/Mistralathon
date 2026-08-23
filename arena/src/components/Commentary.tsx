import { AnimatePresence, motion } from 'framer-motion'
import type { ArenaState, CommentaryEntry } from '../types'

export default function Commentary({ entries, voice }: { entries: CommentaryEntry[]; voice: ArenaState['voice'] }) {
  const latest = entries[entries.length - 1]
  const prev = entries.slice(-4, -1).reverse()

  return (
    <div className="panel commentary">
      <div className="live-tag">
        <i className="px" />
        <span className="eyebrow" style={{ color: 'var(--cream)' }}>
          Live
        </span>
        <span className="eyebrow">· Race control</span>
        {voice.engine === 'mistral' && (
          <span className="eyebrow" style={{ marginLeft: 'auto', color: 'var(--orange)' }}>
            {latest?.source === 'mistral' ? 'Mistral' : 'Race control'}{voice.tts ? ' · Voxtral' : ''}
          </span>
        )}
      </div>
      <div className="commentary-text">
        <AnimatePresence mode="wait">
          {latest && (
            <motion.div
              key={latest.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
            >
              “{latest.text}”
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      <div className="commentary-prev">
        {prev.map((p) => (
          <span key={p.id}>{p.text}</span>
        ))}
      </div>
    </div>
  )
}
