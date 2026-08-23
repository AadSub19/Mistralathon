/** Composed concentric rings + radar sweep. Controlled motion. */
export default function OracleMotif({ active, color }: { active: boolean; color: string }) {
  return (
    <div className="motif" aria-hidden>
      <style>{`
        @keyframes oracle-spin { to { transform: rotate(360deg); } }
        @keyframes oracle-breathe { 0%,100% { opacity: .35 } 50% { opacity: .8 } }
      `}</style>
      <svg
        viewBox="0 0 400 400"
        style={{
          position: 'absolute',
          right: -110,
          top: -90,
          width: 420,
          height: 420,
          transition: 'opacity .5s',
        }}
      >
        {[60, 100, 140, 180].map((r, i) => (
          <circle
            key={r}
            cx="200"
            cy="200"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={i === 1 ? 1.2 : 0.7}
            strokeDasharray={i % 2 ? '2 10' : undefined}
            opacity={0.45 - i * 0.07}
            style={{
              transformOrigin: '200px 200px',
              animation: `oracle-spin ${(active ? 14 : 60) + i * 8}s linear infinite ${i % 2 ? 'reverse' : ''}`,
              transition: 'opacity .4s',
            }}
          />
        ))}
        {/* sweep */}
        <g
          style={{
            transformOrigin: '200px 200px',
            animation: `oracle-spin ${active ? 2.4 : 9}s linear infinite`,
          }}
        >
          <path d="M200 200 L200 20 A180 180 0 0 1 290 44 Z" fill={color} opacity={active ? 0.16 : 0.07} style={{ transition: 'opacity .4s' }} />
          <line x1="200" y1="200" x2="200" y2="20" stroke={color} strokeWidth="1" opacity={0.7} />
        </g>
        <circle cx="200" cy="200" r="3" fill={color} />
        {/* fixed points */}
        {[[120, 150], [250, 260], [300, 130], [150, 290]].map(([x, y], i) => (
          <rect
            key={i}
            x={x}
            y={y}
            width="5"
            height="5"
            fill={color}
            style={{ animation: `oracle-breathe ${3 + i}s ease-in-out infinite` }}
          />
        ))}
      </svg>
      {/* fine dot grid bottom-left */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          bottom: 0,
          width: '55%',
          height: '45%',
          backgroundImage: `radial-gradient(${color} 0.8px, transparent 0.9px)`,
          backgroundSize: '14px 14px',
          opacity: active ? 0.25 : 0.12,
          transition: 'opacity .5s',
          maskImage: 'linear-gradient(45deg, black, transparent 70%)',
          WebkitMaskImage: 'linear-gradient(45deg, black, transparent 70%)',
        }}
      />
    </div>
  )
}
