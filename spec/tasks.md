# Implementation Plan

**HomeOps** — FastAPI + React/Vite. `localStorage` for house data. No auth, no ElevenLabs, no booking.

- Requirements: [requirements.md](./requirements.md)
- Design: [design.md](./design.md)
- Flow preview: `cd frontend && npm run dev`

---

- [x] 1. Scaffold React + Vite frontend
  - House / Live / Work screens in `frontend/`.
  - Vite proxies `/api` to FastAPI `:8000`.
  - _Requirements: 1, 9, 10.1_

- [x] 2. Scaffold FastAPI
  - `app/main.py`, `requirements.txt` (fastapi, uvicorn, httpx, python-dotenv).
  - `/health`; in production mount `frontend/dist` after API routes.
  - uvicorn `0.0.0.0` and `PORT` (default 8000).
  - `.env.example`.
  - _Requirements: 10.1, 10.4_

- [x] 3. House screen + inventory
  - Address, rooms, drawing upload (PNG/JPG/PDF), `localStorage` restore.
  - Reject bad file types.
  - Assets by room; snapshot helper: house JSON → text for the live prompt.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1, 4.2, 4.3_

- [x] 4. Live session (Gemini Live or OpenAI Realtime)
  - `POST /api/live/session` mints credentials.
  - Live screen: camera preview, mic, start/stop, captions.
  - Typed chat fallback if permissions fail.
  - _Requirements: 2.1, 2.5, 2.6, 10.2_

- [x] 5. Save assets from HomeOps
  - Tool `save_asset` writes inventory when confident.
  - Uncertain → ask for the data plate; no save.
  - HomeOps speaks what it stored.
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 6. Exa `lookup_model`
  - `POST /api/tools/exa`; attach summary/URL; say it in session.
  - On failure, keep the visual ID and say lookup failed.
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 7. Problem brief from conversation
  - Same live session: problem, trade, budget, availability.
  - Ask once if budget/availability missing, then continue.
  - Renovation includes drawing notes.
  - Block `call_provider` on gas/fire/uncontrolled flood.
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 8. Apify `find_providers`
  - Trade + address → ~3 callable shops, prefer rating, show on Work screen.
  - Empty: say so, do not call.
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 9. Guava `call_provider` — quote only
  - Outbound call; prompt: HomeOps, AI house super, **do not book**.
  - Cap 3 calls unless user asks; honor “stop”.
  - Webhook + poll: dialing / in-call / done + summary.
  - No calendar, no “you’re booked.”
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 8.4, 10.3_

- [x] 10. Renovation talk-track + activity log
  - Drawings in the brief; over-budget → ask for a better number using only heard prices.
  - Side-by-side notes, not a booking.
  - Activity lines for Exa / Apify / Guava; human-readable errors.
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 9.1, 9.2, 9.3_

- [x] 11. Demo pass
  - Seed: address, bathroom drawing, fridge save + Exa, leak → call test number.
  - Confirm HomeOps never says the job is booked.
  - _Requirements: 2.1, 7.6, 9.1_

---

## Waves

| Wave | Tasks |
| --- | --- |
| 1 | 2, 3 |
| 2 | 4, 5, 6 |
| 3 | 7, 8, 9 |
| 4 | 10, 11 |

If time dies, cut 10 and still demo inventory + one Guava call. The Vite preview is enough to walk judges through the missing reno bit.
