import { useEffect, useRef } from 'react'

/** Pixel-square confetti in the winner's colour + Mistral orange + cream. Premium, not party-store. */
export default function Confetti({ color }: { color: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const resize = () => {
      canvas.width = window.innerWidth * dpr
      canvas.height = window.innerHeight * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)
    const palette = [color, '#ff7a1a', '#f2ebdd', color, '#e8550f']
    const W = () => window.innerWidth
    const H = () => window.innerHeight
    type P = { x: number; y: number; vx: number; vy: number; s: number; r: number; vr: number; c: string; life: number }
    const ps: P[] = []
    const spawn = (n: number, burst: boolean) => {
      for (let i = 0; i < n; i++) {
        const fromCenter = burst
        ps.push({
          x: fromCenter ? W() / 2 + (Math.random() - 0.5) * 120 : Math.random() * W(),
          y: fromCenter ? H() / 2 : -20,
          vx: fromCenter ? (Math.random() - 0.5) * 18 : (Math.random() - 0.5) * 1.5,
          vy: fromCenter ? -Math.random() * 16 - 4 : Math.random() * 1.5 + 1,
          s: 4 + Math.random() * 8,
          r: Math.random() * Math.PI,
          vr: (Math.random() - 0.5) * 0.2,
          c: palette[Math.floor(Math.random() * palette.length)],
          life: 1,
        })
      }
    }
    spawn(180, true)
    let raf = 0
    let t0 = performance.now()
    let drizzle = 0
    const step = (t: number) => {
      const dt = Math.min(40, t - t0) / 16.67
      t0 = t
      ctx.clearRect(0, 0, W(), H())
      drizzle += dt
      if (drizzle > 6 && ps.length < 260) {
        spawn(3, false)
        drizzle = 0
      }
      for (let i = ps.length - 1; i >= 0; i--) {
        const p = ps[i]
        p.vy += 0.22 * dt
        p.vx *= 0.985
        p.x += p.vx * dt
        p.y += p.vy * dt
        p.r += p.vr * dt
        if (p.y > H() + 30) {
          ps.splice(i, 1)
          continue
        }
        ctx.save()
        ctx.translate(p.x, p.y)
        ctx.rotate(p.r)
        ctx.fillStyle = p.c
        ctx.globalAlpha = 0.92
        ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s)
        ctx.restore()
      }
      raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [color])
  return <canvas ref={ref} className="confetti" />
}
