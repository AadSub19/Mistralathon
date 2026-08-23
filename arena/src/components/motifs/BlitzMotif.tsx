/** Kinetic diagonal speed lines. Accelerates on hover. */
export default function BlitzMotif({ active, color }: { active: boolean; color: string }) {
  const lines = Array.from({ length: 9 })
  return (
    <div className="motif" aria-hidden>
      <style>{`
        @keyframes blitz-sweep { from { transform: translateX(-60%) skewX(-28deg); } to { transform: translateX(160%) skewX(-28deg); } }
      `}</style>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
        {lines.map((_, i) => {
          const top = 6 + i * 11
          const w = 90 + ((i * 37) % 120)
          const dur = (active ? 1.1 : 4.2) + ((i * 0.37) % 1.2)
          const delay = -((i * 0.61) % dur)
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                top: `${top}%`,
                left: 0,
                width: `${w}px`,
                height: i % 3 === 0 ? 2 : 1,
                background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
                opacity: active ? 0.75 : 0.35,
                animation: `blitz-sweep ${dur}s linear ${delay}s infinite`,
                transition: 'opacity 0.4s',
              }}
            />
          )
        })}
        {/* corner pixel cluster */}
        <div
          style={{
            position: 'absolute',
            right: 18,
            top: 18,
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 6px)',
            gap: 3,
            opacity: active ? 0.9 : 0.4,
            transition: 'opacity 0.4s',
          }}
        >
          {[1, 0, 0, 1, 1, 0, 1, 1, 1].map((on, i) => (
            <i key={i} style={{ width: 6, height: 6, background: on ? color : 'transparent', display: 'block' }} />
          ))}
        </div>
      </div>
    </div>
  )
}
