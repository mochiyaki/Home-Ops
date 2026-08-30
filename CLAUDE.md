# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

HomeOps — a single-house AI "house super" demo. The homeowner talks to **Ops** (in-app voice agent), Ops identifies an appliance, looks up its manual, finds a local trade, and places an **outbound phone call for a quote**. Two hard product rules run through the whole codebase: **Ops books autonomously, but only a quote at or under the homeowner's budget that fits their availability** (over-budget quotes come back unbooked), and **gas / fire / uncontrolled flood blocks vendor calls** in favor of emergency services.

No auth, no users, one demo house.

## Commands

```bash
# Postgres (terminal 0) — required; the API will not boot without it
docker compose up -d                 # postgres:16 on host port 5434
docker compose down                  # add -v to wipe the volume

# Backend (terminal 1)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (terminal 2) — Vite proxies /api and /health to :8000
cd frontend && npm install && npm run dev     # http://localhost:5173

# Combined: FastAPI serves frontend/dist at / when that folder exists
cd frontend && npm run build && cd .. && uvicorn app.main:app --port 8000

# Guava — the outbound shop-quote caller. Needs GUAVA_API_KEY + GUAVA_AGENT_NUMBER.
python -m guava_agent.agent --chat                 # terminal, no audio, no phone
python -m guava_agent.agent --local                # local mic/speakers
python -m guava_agent.agent --phone +1415...       # live outbound call
guava numbers list                                 # your agent numbers
guava conversations                                # browse past calls
```

# Tests — run against a throwaway homeops_test database
.venv/bin/python -m pytest tests/ -q

# Ops, the homeowner-facing agent (terminal 4)
python -m guava_agent.ops --web      # serves the WebRTC widget
python -m guava_agent.ops --chat     # terminal, no audio
```

```bash
# Old note, now stale:
There is no linter or formatter configured. `spec/` (requirements → design → tasks) is a Kiro-style reference doc, not generated or enforced.

Port 5173 conflicts: use `http://localhost:5173` (IPv6) or `npm run dev -- --port 5174`.

## The mock contract

Every vendor adapter follows the same three-branch shape — do not break it when adding one:

1. Vendor key set → call the real API.
2. No key + `HOMEOPS_MOCK=1` → return a mock whose user-visible strings are prefixed `[MOCK]` and carry `mock: true`.
3. No key, mock off → raise `VendorNotConfigured(vendor, ENV_VAR)`, which `app/main.py` maps to a 503 the frontend renders via `humanError` in `frontend/src/api.js`.

`app/services/guava_caller.py` follows this contract too, which is why an empty `GUAVA_API_KEY` under `HOMEOPS_MOCK=1` silently serves `[MOCK]` results rather than erroring — real calls need the key.

**Dialling is off unless `HOMEOPS_ALLOW_REAL_CALLS=1`.** This is not optional
polish: a test run once inherited a live key from `.env` and rang a real phone
eight times, because `test_call_cap` places calls by design. `will_dial()`
decides before the call row is written, so `POST /api/tools/call` never reports
`mock: false` for a call that gets suppressed. A per-number cooldown caps a
runaway loop at one dial. `tests/conftest.py` blanks every credential and
asserts it before the suite runs.

**Guava is the only voice vendor.** It serves both legs: the outbound shop
call over PSTN and the homeowner-facing Ops agent over WebRTC. There is no
second provider to fall back to, and no provider-selection branch.

`mock: true` propagates up to the UI badge, so mock results are always visibly labeled. `app/errors.py` defines the four exception types; each has a handler in `app/main.py` (503 / 502 / 409 DangerBlocked / 429 CallCapExceeded). Raise these rather than `HTTPException` for vendor and policy failures.

## Architecture

**Persistence — Postgres via `app/db.py`.** `houses` / `assets` / `calls` /
`turns`. Tables are created on startup by the FastAPI lifespan, so a fresh
`docker compose up` needs no migration step. Two engines point at the same
database on purpose: FastAPI routes use the async one through `app/repo.py`,
while Guava's handlers run on plain threads with no event loop and use the
blocking one through `app/store.py`. Do not try to share a pool between them —
asyncpg pools bind to the loop that created them.

`app/store.py` kept the function names of the old in-memory store (`put`,
`get`, `update`, `outbound_count`) so the agent handlers did not change when
this moved to Postgres. The 3-call cap now counts rows, so it survives a
restart.

**Backend — `app/`** (FastAPI, Python 3.12). Keys never leave the server; the browser calls FastAPI, FastAPI calls vendors.

- `routers/tools.py` — `/api/tools/exa` (manual lookup), `/api/tools/providers` (local trades), `/api/tools/call` (place outbound call). The call route is where the two product rules are enforced: `is_danger(brief_text(...))` → `DangerBlocked`, and `repo.outbound_count() >= store.MAX_CALLS` (3) → `CallCapExceeded` unless `try_another`. It calls `guava_caller.will_dial()` **before** writing the call row, so the `mock` flag it returns always matches what actually happened.
- `routers/calls.py` — read-only. `GET /api/calls/{id}` is a cheap poll, `/detail` adds structured fields plus the transcript, `/transcript` is the turns alone, and `GET /api/calls` is history. There is no webhook: Guava's handlers write progress into Postgres themselves, so nothing has to be pulled.
- `routers/voice.py` — mints the in-app Ops session: `mode: "guava"` plus the widget code when `GUAVA_WEBRTC_CODE` is set, otherwise a `browser` mode the frontend fulfills with Web Speech.
- `routers/live.py` — mints an ephemeral Gemini Live (default) or OpenAI Realtime client secret; `LIVE_PROVIDER` selects.
- `store.py` — the **blocking** call-state helpers, for Guava's handler threads only. FastAPI routes use `repo.py` instead. Lookups accept either the local uuid or the provider's own call id.
- `prompt.py` — the single source of HomeOps identity, the shop-call and Ops-voice system prompts, `DANGER_RE`, and brief → spoken-variable conversion. Prompt edits belong here, not inline in services.

**Guava — `guava_agent/agent.py`** (the outbound caller). One `guava.Agent` whose
`on_call_start` builds a `set_task` checklist of typed `guava.Field`s — `can_take_job`,
`quote`, `earliest_window` — so the quote arrives as structured data instead of being
regex-scraped out of the transcript afterwards. `on_question`
answers the shop's appliance questions with a live Exa manual lookup mid-call. The
budget-capped booking rule is typed checklist fields (`booked`, `appointment`) plus `completion_criteria`, not just prose.

After each call it texts the homeowner the outcome via `client.send_sms`
when `HOMEOWNER_PHONE` is set (Guava is SMS-only, no email; the send needs SMS
provisioned on the agent number, else a logged 400 lands in `fields.sms`).
It imports `app/prompt.py` rather than restating the identity, and its handlers write
straight into `app.store` when a `homeops_call_id` variable is present — that is how a
call placed from the API reports progress back to the UI. Run standalone, that variable
is absent and the handlers just write `guava_agent/last_call.json`.

`app/services/guava_caller.py` is the FastAPI side: the Guava SDK's `call_phone` blocks,
so it dials on a daemon thread and returns immediately. `on_agent_speech` /
`on_caller_speech` write each utterance into `turns` as it is spoken, which is
what makes the live transcript possible.

**API contract — `docs/API.md`.** Written for whoever builds the frontend;
keep it current when you change a route.

**Frontend — `frontend/src/`** (React 19 + Vite 7, plain JS, no TypeScript).

- `Root.jsx` — two routes by pathname only: `/overview` → marketing `LandingPage`, everything else → the app inside an iPhone frame.
- `HomeOpsApp.jsx` + `useHouse.js` — persistence. `useLocalHouse` keeps the whole house in `localStorage` under `STORAGE_KEY` and exposes `{house, setHouse}`; `HomeOpsApp.jsx` is the one place that wires it into `App`, so a different store swaps in there without touching a screen.
- `App.jsx` — the orchestrator: screen routing, camera, transcript, and voice lifecycle. Tool calls are no longer routed through the browser; the Ops agent runs them server-side in `guava_agent/ops.py`.
- `agent.js` — the **browser-side fallback agent**. When Guava voice is unavailable, this regex/heuristic turn engine (`runTurn`) reproduces the same flow: infer trade, parse budget/availability, search providers, place the call, `watchCall` polls. It duplicates `DANGER` and the budget-capped booking rules from `prompt.py` in JS — keep the two in sync. **The JS copy is currently narrower than the Python one** and misses phrasings like "water is flooding and I can't stop it"; the backend still blocks these with a 409.
- `voice.js` — `startOpsVoice` loads the Guava WebRTC widget (a self-contained `<script>` that brings its own orb, audio and signaling) and silently degrades to Web Speech recognition + `speechSynthesis`; that degradation is expected, not an error path to fix. The widget owns its own session, so `injectOpsContext` / `sendOpsText` are deliberate no-ops.
- `house.js` — house shape, `SAMPLE` seed, `STORAGE_KEY` (bump the version suffix on shape changes), and `houseSnapshot()` which serializes the house into the prompt text handed to voice agents.

## Deploy

Render (`render.yaml`): one Python web service, `scripts/render-build.sh` installs Python deps then builds the Vite bundle into `frontend/dist`, which `app/main.py` serves with an SPA catch-all. Health check at `/health`. Vendor keys are `sync: false` (set in the dashboard). Any `VITE_*` variable is baked in at build time, so changing one requires a rebuild, not just a restart.
