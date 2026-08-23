#!/usr/bin/env node
/**
 * Generate the QR code PNGs embedded in the READMEs.
 *
 *   npm run qr                                   → uses PUBLIC_ARENA_URL or LAN IP
 *   npm run qr -- https://xxxx.ngrok-free.dev    → explicit base URL
 *
 * Writes:
 *   arena/docs/qr-join.png   BACK YOUR TEAM  → <base>/join
 *   arena/docs/qr-repo.png   project repo    → GitHub
 */
import QRCode from 'qrcode'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const OUT = path.join(__dirname, '..', 'docs')
const REPO_URL = 'https://github.com/AadSub19/Mistralathon'

function lanIp() {
  for (const list of Object.values(os.networkInterfaces())) {
    for (const i of list ?? []) if (i.family === 'IPv4' && !i.internal) return i.address
  }
  return 'localhost'
}

const base = (process.argv[2] ?? process.env.PUBLIC_ARENA_URL ?? `http://${lanIp()}:5173`).replace(/\/$/, '')
const join = `${base}/join`

// Mistral palette: cream modules on near-black, matches the arena.
const opts = { width: 640, margin: 2, errorCorrectionLevel: 'M', color: { dark: '#0a0a0bff', light: '#f2ebddff' } }

await QRCode.toFile(path.join(OUT, 'qr-join.png'), join, opts)
await QRCode.toFile(path.join(OUT, 'qr-repo.png'), REPO_URL, opts)

console.log(`\n  qr-join.png  →  ${join}`)
console.log(`  qr-repo.png  →  ${REPO_URL}\n`)
console.log('  Written to arena/docs/. Commit them so the README QR is live.\n')
