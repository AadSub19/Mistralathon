/** Minimal .env loader (no dotenv dependency). Never overrides real env vars. */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
for (const file of [path.join(__dirname, '..', '.env'), path.join(__dirname, '..', '..', '.env')]) {
  try {
    const text = fs.readFileSync(file, 'utf8')
    for (const raw of text.split('\n')) {
      const line = raw.trim()
      if (!line || line.startsWith('#')) continue
      const eq = line.indexOf('=')
      if (eq < 1) continue
      const key = line.slice(0, eq).trim()
      let val = line.slice(eq + 1).trim()
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) val = val.slice(1, -1)
      if (!(key in process.env)) process.env[key] = val
    }
  } catch {
    /* no file */
  }
}
