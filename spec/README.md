# Spec (Kiro-style, reference)

Hackathon Feature Spec for **HomeOps**. Kiro flow (requirements → design → tasks) in `spec/`, not `.kiro/`.

**HomeOps** is the super for one house: live camera + voice, then a real call to a local trade. Night demo — no auth, no database, no booking.

| File | What it is |
| --- | --- |
| [requirements.md](./requirements.md) | User stories + EARS criteria |
| [design.md](./design.md) | FastAPI + React/Vite + live LLM |
| [tasks.md](./tasks.md) | Implementation order |

**Flow preview:** `cd frontend && npm install && npm run dev` then open the Vite URL (usually http://localhost:5173).

Stack: Python FastAPI backend, React + Vite frontend. Live agent is Gemini Live or OpenAI Realtime.
