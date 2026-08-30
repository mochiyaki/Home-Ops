# HomeOps API

Base URL `http://localhost:8000`. No auth — one demo house.

Start the stack:

```bash
docker compose up -d                              # Postgres on :5434
.venv/bin/uvicorn app.main:app --port 8000        # API + built frontend
.venv/bin/python -m guava_agent.ops --web         # Ops voice agent (WebRTC)
```

Interactive schema: `/docs` (Swagger) and `/openapi.json`.

---

## Conventions

Every response that can be faked carries `mock: true` when it is. Mocked
user-visible strings are prefixed `[MOCK]`. Never hide this in the UI — it is
the contract that keeps a demo honest.

### Error shape

| Status | `error` | Meaning |
|---|---|---|
| 503 | `VendorNotConfigured` | Missing key. Body has `vendor`, `missing` (the env var). |
| 502 | `VendorError` | Vendor call failed. Body has `vendor`, `detail`. |
| 409 | `DangerBlocked` | Gas / fire / uncontrolled flood. **Do not offer a retry.** Tell the user to call emergency services. |
| 429 | `CallCapExceeded` | 3-call cap hit. Retry the same request with `try_another: true`. |

```json
{ "error": "DangerBlocked", "detail": "Gas, fire, or an uncontrolled flood — ..." }
```

---

## Health

### `GET /health`

```json
{ "ok": true, "mock": true, "configured": true, "calls_live": false,
  "suppression_reason": "HOMEOPS_ALLOW_REAL_CALLS is off.",
  "demo_phone": true }
```

- `configured` — Guava credentials are present.
- `calls_live` — a call placed **right now would actually ring a phone**.
  These differ whenever dialling is switched off, which is the default.
- `mock` — inverse of `calls_live`. Drive the status badge off this.
- `suppression_reason` — plain-English why nothing will ring, or `null`.
  Safe to show the user verbatim.
- `dev_shop_phone` — `HOMEOPS_DEV_SHOP_PHONE` is set, so the top-ranked
  `[MOCK]` shop from `/api/tools/providers` carries a real, reachable number
  instead of an unroutable `555` placeholder. The number shown in the UI **is**
  the number dialled; nothing is rewritten at dial time.

### Dialling is off by default

`HOMEOPS_ALLOW_REAL_CALLS` must be `1` before any phone rings. With it off,
`POST /api/tools/call` still works end to end and returns `mock: true` — the
call moves `dialing → in-call → done` and lands a labelled `[MOCK]` summary
naming the shop and the reason. A per-number cooldown
(`HOMEOPS_CALL_COOLDOWN_SECONDS`, default 60) additionally refuses to dial the
same number twice in a row.

---

## House

The house lives server-side so the voice agent and the browser share one record.
It seeds itself on first read.

### `GET /api/house`

```json
{
  "id": "uuid", "slug": "default",
  "address": "1428 Folsom St, San Francisco, CA",
  "homeowner": "Jordan Chen",
  "rooms":    [{ "id": "r1", "name": "Kitchen" }],
  "drawings": [{ "id": "d1", "name": "bathroom-plan.png", "roomId": "r2", "url": "/floor-plan.jpg" }],
  "details":  { "yearBuilt": "1998", "sqft": "1,450" },
  "contacts": [{ "name": "City Plumbing", "trade": "plumber", "phone": "(415) 555-0142" }],
  "assets":   [ /* see below */ ],
  "updated_at": "2026-08-30T02:41:00+00:00"
}
```

### `PATCH /api/house`

Send only what changed: `address`, `homeowner`, `rooms`, `drawings`, `details`,
`contacts`. Returns the full house.

### `GET /api/house/snapshot`

```json
{ "snapshot": "Address: ...\nHomeowner: ...\nRooms: ...\nInventory: ..." }
```

The house as a voice agent sees it. Useful for debugging prompts.

### Assets

`POST /api/house/assets` → `201` · `PATCH /api/house/assets/{id}` · `DELETE /api/house/assets/{id}` → `204`

```json
{
  "id": "uuid", "roomId": "r1", "category": "dishwasher",
  "brand": "Bosch", "model": "SHPM88Z75N", "serial": "",
  "warrantyUntil": "2026-11-01",
  "manualSummary": "", "manualUrl": "", "imageUrl": "/inventory/bosch.jpg"
}
```

`POST`/`PATCH` take the same fields minus `id`.

---

## Tools

### `POST /api/tools/exa` — appliance manual lookup

```json
{ "query": "Bosch SHPM88Z75N leaking under sink" }
→ { "summary": "...", "url": "https://...", "mock": false }
```

### `POST /api/tools/providers` — find local trades

```json
{ "trade": "plumber", "address": "1428 Folsom St, SF" }
→ { "providers": [{ "name": "City Plumbing", "rating": "4.8 (210)",
                    "phone": "(415) 555-0142", "mapsUrl": null }],
    "mock": true }
```

### `POST /api/tools/call` — place the outbound quote call

```json
{
  "phone": "(415) 555-0142",
  "shop_name": "City Plumbing",
  "try_another": false,
  "brief": {
    "address": "1428 Folsom St, SF",
    "problem": "dishwasher leaking under the kitchen sink",
    "trade": "plumber",
    "homeowner": "Jordan Chen",
    "budget": "$300",
    "availability": "weekday mornings",
    "auto_book": true
  }
}
→ { "call_id": "uuid", "mock": false }
```

`mock` is authoritative: `true` means **no phone rang**, whether because a key
is missing or because dialling is switched off. It is decided before the call
record is written, so it never contradicts what actually happened.

Returns **immediately**; the call runs in the background. Poll `/api/calls/{id}`.

Two rules are enforced here, not in the UI:

- `is_danger(brief)` → **409**. Gas, fire, or uncontrolled flood never becomes
  a vendor call.
- 3 calls per install → **429**. Resend with `try_another: true` to override.

---

## Calls

### `GET /api/calls/{id}` — poll (cheap, for the live view)

```json
{ "state": "in-call", "summary": null, "quote": null, "booked": false,
  "appointment": null, "mock": false }
```

`state` is one of `dialing` → `in-call` → `done`, or `failed`.

### `GET /api/calls/{id}/detail` — everything, including transcript

```json
{
  "id": "uuid", "state": "done", "provider": "guava",
  "shop_name": "City Plumbing", "phone": "(415) 555-0142",
  "summary": "City Plumbing quoted $250, soonest Tuesday at ten. ...",
  "quote": "$250 · Tuesday at ten · booked Tuesday at ten",
  "fields": {
    "can_take_job": "yes",
    "quote": "two hundred fifty dollars",
    "earliest_window": "Tuesday at ten",
    "callback_number": null,
    "booked": true,
    "appointment": "Tuesday at ten"
  },
  "booked": true,
  "termination_reason": "bot-hangup",
  "duration_seconds": 74,
  "created_at": "...", "ended_at": "...",
  "transcript": [
    { "seq": 0, "speaker": "agent", "text": "Hi, this is HomeOps...",
      "interrupted": false, "at": "..." },
    { "seq": 1, "speaker": "shop",  "text": "City Plumbing, Dave here.",
      "interrupted": false, "at": "..." }
  ]
}
```

`fields` is extracted by the voice agent's typed checklist, **not** regex-scraped
from the transcript. `booked` is `true` only when the quote fit the budget and
availability and the agent confirmed the slot on the call.

### `GET /api/calls/{id}/transcript`

Just the `transcript` array above. Poll this during a live call; turns are
written as they are spoken.

### `GET /api/calls?limit=50`

Call history, newest first, same shape as `/detail` minus `transcript`.

---

## Voice

### `POST /api/voice/web` — mint the in-app Ops session

```json
{ "house_snapshot": "..." }
→ { "mode": "guava",
    "webrtc_code": "grtc-...",
    "first_message": "Hey — I'm Ops, your house super. ...",
    "mock": false }
```

`mode` is `guava` (load the widget with `webrtc_code`) or `browser` (the
Web Speech fallback, used when no code is configured). For `guava`, inject:

```html
<script src="https://app.goguava.ai/static/build/webrtc-widgets/guava-widget-audio-orb.js"
        data-webrtc-code="grtc-..."></script>
```

The widget is self-contained — it brings its own orb, audio and signaling.
**The Ops agent must be running** (`python -m guava_agent.ops --web`) or the
code answers to nobody.

### `POST /api/live/session`

Ephemeral Gemini/OpenAI Realtime secret. Unused by the Guava path.


---

## Architecture notes for the frontend

- `POST /api/tools/call` is fire-and-forget. The Guava agent writes progress
  into Postgres from its own thread; polling is the only sync mechanism.
- A call reaching `done` **does not** mean the checklist completed. A shop can
  hang up early — `fields` will hold whatever was captured and
  `termination_reason` explains the ending. Render partial results.
- `booked: true` means the agent confirmed the appointment on the call —
  surface who is coming and when. Over-budget quotes come back with
  `booked: false` for the homeowner to decide.

---

## Note for the frontend agent

Four files under `frontend/` were already changed while the backend moved to
Guava. Read these before editing, they are easy to clobber:

| File | Change |
|---|---|
| `src/api.js` | `placeCall(phone, brief, tryAnother, shopName)` — now sends `shop_name` |
| `src/agent.js` | passes `shop.name` into `placeCall` |
| `src/voice.js` | rewritten for Guava only; `startOpsVoice({ webrtcCode, mode, onState, onTranscript, onError })` |
| `src/App.jsx` | passes `webrtcCode: session.webrtc_code` into `startOpsVoice` |

### Outstanding: duplicated danger rule

`frontend/src/agent.js` carries its own JS copy of the danger regex, mirroring
`DANGER_RE` in `app/prompt.py`. The Python side was widened to catch phrasings
that were slipping through:

- `burst pipe`, `water everywhere`
- `can't stop / shut off / turn off` + `the water | flooding | leak | it`
- `"water is flooding and I can't stop it"` — the two halves arrive apart

**The JS copy still has the old, narrower pattern.** The backend blocks these
regardless (`POST /api/tools/call` returns 409), so this is not a safety hole —
but the browser-side agent will offer to call a plumber for a flood it should
be refusing. Worth syncing.

### Things the UI should surface

- `GET /health` → `demo_phone: true` means every dial is redirected to one
  number. Say so on screen rather than letting it look like a real dial.
- `GET /api/calls/{id}/transcript` is written live — poll it during a call.
- A call can reach `done` with partial `fields` if the shop hung up early.
  Render what is there; `termination_reason` explains the ending.
