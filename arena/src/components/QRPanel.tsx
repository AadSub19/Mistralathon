import { QRCodeSVG } from 'qrcode.react'

export default function QRPanel({ url, locked, compact }: { url: string; locked: boolean; compact: boolean }) {
  const join = `${url}/join`
  return (
    <div className="panel qr-panel">
      <div className="qr-box">
        <QRCodeSVG value={join} size={compact ? 124 : 156} bgColor="#f2ebdd" fgColor="#0a0a0b" level="M" />
      </div>
      <div className="qr-copy">
        <span className="eyebrow">Audience</span>
        <div className="qr-head display">BACK YOUR TEAM</div>
        <div className="qr-url">{join.replace(/^https?:\/\//, '')}</div>
        {locked ? (
          <span className="locked-badge">
            <i className="px" style={{ background: 'var(--cream-3)' }} /> Picks locked
          </span>
        ) : (
          <div className="qr-hint">Scan, type your name, pick a team. Free to switch until picks lock.</div>
        )}
      </div>
    </div>
  )
}
