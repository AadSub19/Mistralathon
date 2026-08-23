import { motion } from 'framer-motion'
import type { TeamMeta } from '../teams'
import type { Supporter } from '../types'
import Confetti from './Confetti'
import BlitzMotif from './motifs/BlitzMotif'
import OracleMotif from './motifs/OracleMotif'
import MaverickMotif from './motifs/MaverickMotif'

export default function WinnerOverlay({ team, supporters }: { team: TeamMeta; supporters: Supporter[] }) {
  const Motif = team.id === 'blitz' ? BlitzMotif : team.id === 'oracle' ? OracleMotif : MaverickMotif
  const n = supporters.length
  const names = [...supporters].sort((a, b) => a.ts - b.ts).map((s) => s.name)
  const MAX = 40
  const shown = names.slice(0, MAX)
  const rest = names.length - shown.length
  const pretty = team.name.charAt(0) + team.name.slice(1).toLowerCase()

  return (
    <motion.div className="winner-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.5 }}>
      <Confetti color={team.color} />
      <motion.div
        className="winner-card"
        style={{ ['--team' as string]: team.color }}
        initial={{ scale: 0.72, opacity: 0, y: 30 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 140, damping: 18, delay: 0.15 }}
      >
        <Motif active color={team.color} />
        <motion.div className="winner-glyph" initial={{ scale: 0, rotate: -30 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: 'spring', stiffness: 200, damping: 12, delay: 0.45 }}>
          {team.glyph}
        </motion.div>
        <motion.h1 className="winner-headline display" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6, duration: 0.5 }}>
          <span className="wn">🏆 {team.name}</span>
          <span className="wl">WINS THE PIZZA GRAND PRIX</span>
        </motion.h1>
        <motion.div className="winner-sub" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.3, duration: 0.6 }}>
          THE CROWD CALLED IT
        </motion.div>
        <motion.div className="winner-count" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.6, duration: 0.5 }}>
          <b>{n}</b> {n === 1 ? 'person' : 'people'} backed {pretty}
        </motion.div>
        <div className="winner-names">
          {shown.map((name, i) => (
            <motion.span
              key={i}
              className="name-chip"
              initial={{ opacity: 0, y: 10, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: 1.9 + i * 0.05, type: 'spring', stiffness: 300, damping: 18 }}
            >
              {name}
            </motion.span>
          ))}
          {rest > 0 && (
            <motion.span className="name-chip" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.9 + shown.length * 0.05 }}>
              +{rest} more
            </motion.span>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}
