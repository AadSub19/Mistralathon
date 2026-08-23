<div align="center">

# 🏁 MISTRALATHON
## PIZZA GRAND PRIX

**The first live spectator sport for autonomous AI agents.**

*Three Mistral teams. One real-world challenge. First pizza through the door wins.*

</div>

---

Everyone at this hackathon is building with **Mistral Vibe**. So we asked the obvious question:

> **What happens when you put Mistral teams against each other — in the real world — with a crowd watching?**

Not a benchmark. Not a leaderboard. A **race.** With a start light, a live timer, a roaring commentary
feed, an audience that picks a side from their phones, and a finish line you can *eat*.

Three Mistral-powered teams receive the same challenge at the same moment. Each one independently
designs, builds, and tests its own **Pizza Agent** — live, on stage, using real Mistral Vibe sessions.
Then the agents are released into the real internet to order a real pizza to a real door.

**The physical pizza decides the winner.** No judges. No vibes. Just delivery.

---

## 🍕 THE CHALLENGE

<table>
<tr><td>🎯 <b>Order</b></td><td>One <b>pepperoni + jalapeño</b> pizza, for delivery</td></tr>
<tr><td>💸 <b>Budget</b></td><td>Delivered total <b>≤ $35</b> — fees, tax, everything</td></tr>
<tr><td>🏆 <b>Win</b></td><td><b>First qualifying pizza delivered</b></td></tr>
<tr><td>🛡️ <b>Rules</b></td><td>One order only · legitimate sites only · never bypass CAPTCHA, MFA, auth, or payment security</td></tr>
</table>

That's it. That's the whole brief. Everything else — which site, which restaurant, which path — the
agents figure out themselves. *(Spec: [`shared/challenge.json`](shared/challenge.json))*

---

## 🏎️ THE GRID

Three teams. Three personalities. **Zero pre-programmed strategy.** They get the challenge, not a playbook.

<table>
<tr>
<td width="33%" align="center">
<h3>⚡ BLITZ</h3>
<b>THE INSTINCT</b><br/><br/>
<i>Fast decisions.<br/>Relentless momentum.<br/>No hesitation.</i>
</td>
<td width="33%" align="center">
<h3>🔮 ORACLE</h3>
<b>THE VISION</b><br/><br/>
<i>Predictive. Calculated.<br/>Always thinking beyond<br/>the next move.</i>
</td>
<td width="33%" align="center">
<h3>🃏 MAVERICK</h3>
<b>THE WILDCARD</b><br/><br/>
<i>Unpredictable. Adaptive.<br/>Finds routes others<br/>never see.</i>
</td>
</tr>
</table>

Which one would *you* back?

---

## 📱 BACK YOUR TEAM — THE QR CODE

This is where the audience stops being an audience.

On the big screen, under **BACK YOUR TEAM**, there's a QR code. Scan it with your phone and you're in.

<div align="center">

<img src="arena/docs/qr-join.png" width="280" alt="BACK YOUR TEAM — scan to join" />

### 📱 BACK YOUR TEAM
**https://sandbar-onboard-reorder.ngrok-free.dev/join**

*scan → name → pick · No app. No account. No money. Ten seconds.*

</div>

> 🔁 **This QR is live for the current event tunnel.** If the URL changes, regenerate it in one command:
> `cd arena && npm run qr -- https://<new-url>` — then commit `arena/docs/qr-join.png`.

**What happens when you scan it:**

1. 📝 **Type your first name.** That's the whole sign-up.
2. ⚡🔮🃏 **Tap a team.** Blitz, Oracle, or Maverick.
3. 🔥 **BACK THIS TEAM.** Done.

**What happens on the big screen — instantly:**

- Your team's card **pulses.**
- The supporter count **ticks up.**
- Your name **flashes on the card** — `+ Aisha` — for everyone in the room to see.
- You join the crowd under your team: `Aisha · Daniel · Rohan · +9`

**What happens on your phone:**

> **You're backing ORACLE 🔮**
> *Now watch the Mistralathon.*

**The fine print (it's short):**

- 🔄 **Changed your mind?** Tap *Change my pick* — until the host **locks picks** before the race. Then you're committed. Choose wisely.
- 🙅 **No accounts. No credits. No money. No download.** It's a web page. Your phone remembers you so you can't accidentally vote twice.
- 📶 Works on the venue Wi-Fi — or **cellular works too.**

**And at the finish line:**

When the pizza arrives and the winner is declared, the whole screen transforms. The losing cards fade.
The winner expands. And then:

> ### 🏆 ORACLE WINS THE PIZZA GRAND PRIX
> ### THE CROWD CALLED IT
> **12 people backed Oracle** — and every one of their names goes up on the screen.

Your phone flips to the result at the same moment: *"You called it."* — or *"Next time."*

**Be on that screen. Scan the code.**

---

## 📺 THE BROADCAST

The arena isn't a dashboard. It's a sports broadcast for machines — designed to be projected on a wall
and make people walking past **stop.**

| Phase | What the room sees |
|---|---|
| 🟢 **LOBBY** | The challenge, the grid, the QR. Cards hover and breathe — each team moves differently. The crowd builds. |
| 🔨 **BUILDING** | Lights flicker on. Each team's card lights up milestone blocks as its Pizza Agent takes shape — blueprint, assembly, stress-test, *ready to race.* |
| 🔴 **RACING** | **Lights out.** Elapsed timer running. Every observable move streams onto the cards: `Opened dominos.com` · `Restaurant discovered` · `Cart updated · $18.49` · `Checkout reached`. Race control narrates: *"Oracle has entered checkout while Blitz is still building a cart. Maverick just changed direction."* |
| 🏆 **WINNER** | The pizza arrives. The host hits **Declare Winner.** Confetti — in Mistral pixels. Names on screen. The final frame. |

**What you never see:** the agents' reasoning. The arena shows only *observable actions* — what the agent
actually did — never what it was thinking. The teams' strategies are theirs.

---

## ⚙️ UNDER THE HOOD

```
 shared/challenge.json ──────────────────────────────────────────────────────┐
                                                                             ▼
 orchestrator/run_team.py <team>       real Mistral Vibe CLI sessions, one team at a time
      Architect ──► Developer ──► QA   (isolated workdirs · auto-approve · turn & token caps)
                    │
                    ▼
 runs/<team>/PLAN.md · pizza-agent/agent_spec.json · QA_REPORT.md
 runs/<team>/events.jsonl   ◄── every observable action, appended live, one JSON line each
                    │
                    ▼
 execution/                 the Pizza Agent drives a real browser through a fixed tool contract:
                            navigate · click · type_into · visible_page_text · screenshot · current_url · cart_state
                    │
                    ▼
 arena/                     tails events.jsonl → race activity, milestones, commentary, QR, winner moment
```

**Build** — Three Vibe subprocesses per team (Architect → Developer → QA) produce a plan, an agent spec,
and a QA report. Every step is logged as an event.

**Race** — The agent gets seven browser tools and the challenge. Nothing else.

**Watch** — The arena reads `runs/<team>/events.jsonl` every second. New team file appears? It picks it
up automatically. No file yet? It shows mock activity so the screen is never dark during a demo.

```json
{"ts": "2026-08-22T20:14:10Z", "team": "oracle", "phase": "qa", "actor": "qa", "action": "agent_ready", "detail": "Agent is ready for execution"}
```

---

## 🚀 RUN IT

### 1 · Build a team's agent

```bash
python orchestrator/run_team.py oracle            # real Mistral Vibe sessions
python orchestrator/run_team.py oracle --mock     # deterministic, no API calls
python orchestrator/run_team.py oracle --phase qa # one phase only
```

### 2 · Light up the arena

```bash
cd arena
npm install
npm run dev
```

```
  ╔══════════════════════════════════════════════╗
  ║   MISTRALATHON · PIZZA GRAND PRIX · ARENA     ║
  ╚══════════════════════════════════════════════╝

  Host screen     http://192.168.1.42:5173/
  JOIN (phones)   http://192.168.1.42:5173/join   ◀ scan / open this on phones
```

Open the **Host screen** on the projector laptop. Full-screen it. The QR on screen encodes the **JOIN** URL.

**Venue Wi-Fi won't let phones reach your laptop?** (Most event networks isolate devices.) Tunnel it — phones then work on Wi-Fi *or* cellular:

```bash
ngrok http 5173                                               # second terminal, copy the https URL
PUBLIC_ARENA_URL=https://xxxx.ngrok-free.dev npm run dev      # QR now points at the tunnel
```

### 3 · Run the race

Tiny ⚙ button, bottom-right of the host screen:

**Lobby** → crowd backs teams → **Lock picks** → **Building** → **Racing** → pizza arrives → **Declare winner** 🏆

Full arena docs, env vars, and API: [`arena/README.md`](arena/README.md)

---

## 🗂️ REPO

```
arena/          The broadcast — React · TypeScript · Vite · Framer Motion · Express
orchestrator/   run_team.py — Architect → Developer → QA via Mistral Vibe CLI
execution/      Browser execution layer + tool contract for Pizza Agents
shared/         challenge.json · event_logger.py (the event schema everyone writes)
teams/          teams/<team>/personality.md
runs/           Generated artifacts + events.jsonl per team
```

## 🎙️ WHAT'S NEXT

- **Voxtral commentary.** The arena's commentary feed sits behind one function — `publishCommentary(text)` — and a 🎙 toggle already wired for audio. Plug in Mistral-generated play-by-play and Voxtral voice, and race control speaks.
- **More teams on the grid.** The challenge is generic. The grid isn't limited to three.
- **Different challenges.** Pizza today. Anything with a doorbell tomorrow.

## 🛡️ SAFETY

One order, ever. Legitimate sites only. No bypassing CAPTCHA, MFA, auth, access controls, or payment
security — it's in the challenge spec and every agent's constraints. Authenticated browser sessions and
payment data are git-ignored.

---

<div align="center">

<img src="arena/docs/qr-repo.png" width="160" alt="Scan for the repo" />

*Scan for this repo.*

**Built at the Mistral Vibe Hackathon.**

*Scan the code. Pick a side. Watch the machines race for dinner.*

</div>
