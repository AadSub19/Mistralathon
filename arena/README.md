# 🏁 ARENA — the Pizza Grand Prix broadcast

This is the screen that makes people stop walking.

Three animated team cards with three different motion personalities. A **BACK YOUR TEAM** QR code
that turns the room into a crowd. Live race activity translated straight from agent events. A
race-control commentary feed. An elapsed timer. And a winner moment built to be the last frame of
the demo video — losing cards fade, the winner expands, Mistral-pixel confetti falls, and every
supporter's name goes up on the wall under **THE CROWD CALLED IT.**

Plus the phone page at `/join`: name → team → **BACK THIS TEAM**. Ten seconds, no account.

Stack: React 18 · TypeScript · Vite · Framer Motion · `qrcode.react` · Express (in-memory, 1s polling).
Dark ground, Mistral orange, cream type, pixel motifs. Built for a 16:9 projector.

## The QR code

<div align="center">
<img src="docs/qr-join.png" width="220" alt="BACK YOUR TEAM QR" /><br/>
<b>https://sandbar-onboard-reorder.ngrok-free.dev/join</b><br/>
<sub>Regenerate for a new URL: <code>npm run qr -- https://&lt;base-url&gt;</code> → writes <code>docs/qr-join.png</code> + <code>docs/qr-repo.png</code></sub>
</div>

The QR on the host screen encodes **`<PUBLIC_ARENA_URL>/join`**. The server derives the URL from the
laptop's LAN IP so phones on the same network can reach it — it is **never `localhost`** (a phone can't
reach your laptop's localhost). Override with `PUBLIC_ARENA_URL` for tunnels or a specific interface.

Scan → the phone page opens → name + team → the host screen updates within a second: card pulse,
count animates up, `+ Name` flashes, name joins the supporter list. People can switch teams until
the host **locks picks**; after that the phone shows "Picks locked". When a winner is declared, every
phone flips to the result — *"You called it."* or *"Next time."*

## Run

```bash
npm install      # first time
npm run dev
```

```
  Host screen     http://<LAN-IP>:5173/         ← open on the projector laptop, full-screen
  JOIN (phones)   http://<LAN-IP>:5173/join     ← what the QR encodes
  events · oracle   file  …/runs/oracle/events.jsonl
  events · blitz    mock  …/runs/blitz/events.jsonl
```

Single-port production build (optional): `npm run build && npm start` → `http://<LAN-IP>:8787`.

### Venue Wi-Fi blocks phone → laptop?

Most event networks isolate clients. Tunnel it (works on phone Wi-Fi or cellular):

```bash
ngrok http 5173                       # in a second terminal; copy the https URL
PUBLIC_ARENA_URL=https://xxxx.ngrok-free.dev npm run dev
```

Or put laptop + phones on a personal hotspot and run plain `npm run dev`.

### Environment

| Variable | Default | Purpose |
|---|---|---|
| `PUBLIC_ARENA_URL` | `http://<LAN-IP>:<port>` | Base URL encoded in the QR code. Never localhost. |
| `ARENA_MOCK` | _(auto)_ | `1` mock events for all teams · `0` never mock · unset = mock only for teams with no `events.jsonl` |
| `ARENA_RUNS_DIR` | `../runs` | Where to look for `<team>/events.jsonl` |
| `PORT` | `8787` | API server port |
| `MISTRAL_API_KEY` | — | Enables Mistral commentary + Voxtral voice |
| `VOXTRAL_VOICE_ID` / `VOXTRAL_VOICE_NAME` | `Oliver - Excited` | Voice to use (any preset name, e.g. `Paul - Confident`) |
| `VOXTRAL_TTS` | `1` | `0` = Mistral text only, no audio |
| `COMMENTARY_INTERVAL_MS` | `7000` | Min gap between Mistral lines |

See `env.example`.

## Running the show

Small ⚙ button, bottom-right of the host screen (deliberately unobtrusive):

| Control | Effect |
|---|---|
| **Lobby / Building / Racing** | Switch phase. Racing starts the elapsed timer and activates commentary. |
| **Lock / Unlock picks** | Freeze phone submissions. Phones show "Picks locked". |
| **Declare winner** ⚡ 🔮 🃏 | Winner overlay, other cards dim, phones flip to the result. Picks auto-lock. |
| **Undo winner** | Back to Racing. |
| **Reset arena** | Clears supporters, phase, winner, mock events. |
| **🎙 Commentary** (header) | Toggles audio for every new commentary line — see Voxtral hook below. |

Same via curl:

```bash
curl -X POST localhost:8787/api/admin/phase  -H 'content-type: application/json' -d '{"phase":"racing"}'
curl -X POST localhost:8787/api/admin/lock   -H 'content-type: application/json' -d '{"locked":true}'
curl -X POST localhost:8787/api/admin/winner -H 'content-type: application/json' -d '{"team":"oracle"}'
curl -X POST localhost:8787/api/admin/reset
```

## Audience flow (`/join`)

Name → tap a team → **BACK THIS TEAM** → "You're backing ORACLE 🔮 · Now watch the Mistralathon."
A per-browser ID in `localStorage` prevents duplicate votes; people can change their pick until
the host locks. No accounts, no credits, no money.

## Live events

The server reads `runs/<team>/events.jsonl` (one JSON object per line:
`ts, team, phase, actor, action, detail`) every second and picks up new files automatically.
Per team, if no file exists a mock generator produces plausible *observable* events so the
screen can be demoed.

`src/lib/translate.ts` maps `action` → human-readable activity and a 6-block milestone
progress bar. Unknown actions are humanised from their name only; `detail` is never dumped
to screen, so no reasoning can leak. Build-role names (Architect/Developer/QA) are never shown.

Add new execution actions in the `LABELS` table there.

## Commentary — Mistral + Voxtral

Race control is a two-stage pipeline, both stages optional:

```
runs/<team>/events.jsonl ──► server/commentary.ts (deterministic)  ──► publishCommentary()
                        └──► server/voxtral.ts  (Mistral chat)     ──┘        │
                                                                              ▼
                                             Voxtral TTS (/v1/audio/speech) → mp3 → host screen
```

**Enable it:** put `MISTRAL_API_KEY=...` in `arena/.env` (see `env.example`) and restart `npm run dev`.
The banner then shows `commentary Mistral · mistral-small-latest` and `voice Voxtral · voxtral-mini-tts-2603`.

- **Text** — every burst of new events (min 7 s apart) is summarised into one sentence of play-by-play
  by Mistral. The prompt receives **observable actions only** (action names, hostnames, sanitised
  details) and is instructed never to speculate about reasoning or reveal build-role names. Any
  failure falls back to the deterministic formatter, so the feed never goes quiet.
- **Voice** — click **🎙 Voxtral** in the header. The toggle is server-side, so TTS only spends
  money while it's on. Each new line is synthesised to mp3, cached, served at
  `GET /api/commentary/:id/audio`, and played on the host screen in order (stale lines are dropped so
  audio never lags the race). Without a key the same toggle uses the browser's built-in voice.
- **Manual lines** — `POST /api/commentary {"text": "..."}` publishes (and voices) anything:
  host announcements, a second commentator, whatever.

Voice selection: the server lists preset voices at boot and picks **"Oliver - Excited"** (energetic,
crisp, British — proper race commentary), falling back to Paul - Confident. Override with
`VOXTRAL_VOICE_NAME="Paul - Confident"` or `VOXTRAL_VOICE_ID=...`. Presets include Paul / Oliver / Jane
(en) and Marie (fr) in Neutral, Happy, Excited, Confident, Cheerful and more.

## API

```
GET  /api/state            full snapshot: supporters, phase, winner, raceStartedAt, events, commentary, publicUrl
POST /api/support          {id, name, team}      → 423 if picks are locked
GET  /api/support/:id      my pick + lock/phase/winner (phones poll this)
POST /api/admin/lock       {locked: boolean}
POST /api/admin/phase      {phase: lobby|building|racing|winner}
POST /api/admin/winner     {team | null}
POST /api/admin/reset
POST /api/commentary       {text}                → published + voiced
GET  /api/commentary/:id/audio                    Voxtral mp3 for a line (404 until ready)
POST /api/admin/audio      {enabled: boolean}     host 🎙 toggle (shared)
```

## Layout

```
server/   index.ts (API, LAN-IP/QR URL, static in prod) · state.ts · events.ts (file + mock) · commentary.ts · voxtral.ts (Mistral text + Voxtral TTS) · env.ts
src/
  pages/        Arena.tsx (host) · Join.tsx (phone)
  components/   Header · TeamCard · Commentary · QRPanel · Challenge · HostControls · WinnerOverlay · Confetti
  components/motifs/  BlitzMotif (speed lines) · OracleMotif (rings + sweep) · MaverickMotif (reshuffling pixels)
  lib/          translate.ts (events → activity) · commentary.ts (audio hook)
  teams.ts · api.ts (polling hook) · types.ts · styles/global.css
```

Design: near-black ground, Mistral orange accent, cream type, pixel-block motifs;
Syne for display, Inter for body, JetBrains Mono for telemetry. Optimised for 16:9 projection.
