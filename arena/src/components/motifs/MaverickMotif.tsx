import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'

/** Scattered pixel blocks that reshuffle to new positions — asymmetric, surprising. */
export default function MaverickMotif({ active, color }: { active: boolean; color: string }) {
  const [seed, setSeed] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setSeed((s) => s + 1), active ? 900 : 3600)
    return () => window.clearInterval(id)
  }, [active])

  const blocks = useMemo(() => {
    // deterministic pseudo-random from seed
    let x = seed * 9301 + 49297
    const rnd = () => {
      x = (x * 9301 + 49297) % 233280
      return x / 233280
    }
    return Array.from({ length: 16 }).map((_, i) => ({
      id: i,
      left: 4 + rnd() * 92,
      top: 4 + rnd() * 92,
      size: 5 + Math.round(rnd() * 3) * 4,
      rot: Math.round(rnd() * 3) * 45,
      o: 0.2 + rnd() * 0.6,
    }))
  }, [seed])

  return (
    <div className="motif" aria-hidden>
      {blocks.map((b) => (
        <motion.div
          key={b.id}
          animate={{ left: `${b.left}%`, top: `${b.top}%`, rotate: b.rot, opacity: b.o, width: b.size, height: b.size }}
          transition={{ type: 'spring', stiffness: active ? 140 : 40, damping: active ? 12 : 18, mass: 0.8 }}
          style={{ position: 'absolute', background: color }}
        />
      ))}
      {/* an off-axis stroke */}
      <motion.div
        animate={{ rotate: active ? [12, -8, 12] : 12, x: active ? [0, 40, 0] : 0 }}
        transition={{ duration: active ? 1.8 : 0.6, repeat: active ? Infinity : 0, ease: 'easeInOut' }}
        style={{
          position: 'absolute',
          left: '-10%',
          top: '62%',
          width: '70%',
          height: 1,
          background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
          opacity: 0.5,
        }}
      />
    </div>
  )
}
