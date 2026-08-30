# Requirements Document

## Introduction

**HomeOps** is a hackathon demo of an AI house super. The homeowner talks to a **live multimodal agent** (Gemini Live or OpenAI Realtime) with the camera on. The agent builds a house inventory from what it sees. When something breaks or a renovation comes up, HomeOps finds highly rated local providers and **calls them**.

There is no account and no booking. House memory is stored in the browser. The demo ends when HomeOps has called a provider and brought back what they said (price, availability, or a decline).

Backend is **Python / FastAPI**. The UI is **React + Vite**. In development, Vite serves the app and proxies `/api` to FastAPI. For a combined demo, FastAPI serves the Vite `dist/` build.

This document specifies **what** the demo must do. Architecture lives in `design.md`. Confirm the screens with `cd frontend && npm run dev`.

### Actors

- **Homeowner**: whoever is at the laptop (no login).
- **Service provider**: plumber, appliance tech, or contractor reached by phone.
- **HomeOps**: live LLM with tools (look up models, search local pros, place a call).

### In scope

- One house (localStorage): address, rooms, uploaded drawings, appliances.
- Live camera + voice session to register inventory and report problems.
- Exa lookup for appliance model / manual / parts.
- Apify (Google) search for high-rated local providers.
- Guava outbound call that uses inventory, drawings, budget, and availability as the brief.
- Show call status and what the provider said.
- Renovation talk-track: use stored drawings, call contractors, ask for a better price if a number comes back high.

### Out of scope

- Auth, users, households, invites.
- Auth, Node, Next.js, any hosted database. The one demo house lives in the browser (no users).
- ElevenLabs (the live LLM already speaks).
- Booking, scheduling, payments, SMS confirmations, auto-book.
- Provider portals, permits, insurance, IoT.

---

## Requirements

### Requirement 1: House in the browser

**User Story:** As a homeowner, I want to jot down my address, rooms, and drawings, so that HomeOps has a house to manage during the demo.

#### Acceptance Criteria

1. WHEN the homeowner enters an address THEN THE SYSTEM SHALL keep that address in the browser and show it in the House screen.
2. WHEN the homeowner adds or edits rooms THEN THE SYSTEM SHALL keep a room list HomeOps can name (Kitchen, Bathroom, …).
3. WHEN the homeowner uploads a drawing (PNG, JPG, or PDF) THEN THE SYSTEM SHALL attach it to the house and make it available to HomeOps as context.
4. WHEN the page is refreshed THEN THE SYSTEM SHALL restore the last house, rooms, drawings, and assets from browser storage.
5. IF an upload is not PNG/JPG/PDF THEN THE SYSTEM SHALL reject it with a short message.

### Requirement 2: Live camera-and-voice agent

**User Story:** As a homeowner, I want to point the camera and talk, so that I am not filling forms to register appliances or explain a leak.

#### Acceptance Criteria

1. WHEN the homeowner starts a session THEN THE SYSTEM SHALL open a live multimodal LLM session (Gemini Live or OpenAI Realtime), show a camera preview, and stream microphone audio.
2. WHEN the homeowner points at an appliance and talks THEN THE SYSTEM SHALL use live audio plus video (or sampled frames) to identify category, brand, and model when visible or spoken.
3. WHEN HomeOps is confident THEN THE SYSTEM SHALL add that appliance to the house inventory (room, brand, model, a still frame) and say what it saved.
4. WHEN HomeOps is not confident THEN THE SYSTEM SHALL ask to see the data plate or hear the model instead of saving a guess.
5. WHEN the homeowner describes a problem (leak, broken fridge, renovate the bathroom) THEN THE SYSTEM SHALL handle it in the **same** live session — not a separate ticket form.
6. IF camera or mic is denied THEN THE SYSTEM SHALL say so and still allow typed chat into the same agent.

### Requirement 3: Model lookup with Exa

**User Story:** As a homeowner, I want HomeOps to look up the model it just saw, so that the inventory is more than a name.

#### Acceptance Criteria

1. WHEN a model is identified THEN THE SYSTEM SHALL call Exa for a manual, key specs, or common parts.
2. WHEN Exa returns a result THEN THE SYSTEM SHALL attach a short summary (and a URL if present) to that asset and mention it in the live conversation.
3. IF Exa fails or times out THEN THE SYSTEM SHALL keep the visual ID and say the lookup did not come back.

### Requirement 4: Inventory HomeOps can use

**User Story:** As a homeowner, I want to see what the house already knows, so that when I say the fridge is broken HomeOps does not ask for the model again.

#### Acceptance Criteria

1. WHEN the homeowner opens inventory THEN THE SYSTEM SHALL list assets by room with brand, model, and any Exa notes.
2. WHEN the live agent handles a problem THEN THE SYSTEM SHALL inject the current inventory and drawings into the session context.
3. WHEN the homeowner names a known room or appliance THEN THE SYSTEM SHALL use that record in the provider brief.

### Requirement 5: Problem, budget, availability

**User Story:** As a homeowner, I want to tell HomeOps what is wrong, my budget, and when I am around, so that the call to a pro is specific.

#### Acceptance Criteria

1. WHEN the homeowner describes a problem in the live session THEN THE SYSTEM SHALL capture a short brief: what is wrong, likely trade, budget if given, availability if given.
2. WHEN budget or availability is missing THEN THE SYSTEM SHALL ask once, then proceed without them if the homeowner does not care.
3. WHEN the problem is a renovation THEN THE SYSTEM SHALL include relevant drawings in the brief.
4. IF the homeowner describes immediate danger (gas, fire, flooding they cannot stop) THEN THE SYSTEM SHALL tell them to call emergency services and SHALL NOT place a vendor call as a substitute.

### Requirement 6: Find local providers

**User Story:** As a homeowner, I want HomeOps to find highly rated nearby providers, so that I am not Googling while water is on the floor.

#### Acceptance Criteria

1. WHEN HomeOps knows the trade and house address THEN THE SYSTEM SHALL search local providers (Apify Google/Maps scrape, optionally Exa) for that trade near the address.
2. WHEN results return THEN THE SYSTEM SHALL pick a small set (about 3) with a phone number, preferring higher ratings.
3. WHEN candidates are chosen THEN THE SYSTEM SHALL show name, rating, and phone on the Work screen.
4. IF none are callable THEN THE SYSTEM SHALL say so and not place a call.

### Requirement 7: Call the provider (no booking)

**User Story:** As a homeowner, I want HomeOps to call the shop for me, so that I hear back a price or a window — not a booked appointment the demo cannot honor.

#### Acceptance Criteria

1. WHEN the homeowner agrees to call (or asks HomeOps to handle it) THEN THE SYSTEM SHALL place an outbound Guava call to a candidate with a phone number.
2. WHEN the call connects THEN THE SYSTEM SHALL identify itself as HomeOps, an AI house super calling on behalf of the household, and SHALL use the job brief (inventory, drawings mention, budget, availability).
3. WHEN the provider gives a price, a time window, or a no THEN THE SYSTEM SHALL show that outcome on the Work screen.
4. WHEN the call does not connect THEN THE SYSTEM SHALL say so and offer to try the next candidate.
5. WHILE a call is in progress THEN THE SYSTEM SHALL show dialing / in-call / done.
6. THE SYSTEM SHALL NOT book, confirm a slot, or promise the provider that the homeowner is locked in.
7. THE SYSTEM SHALL NOT call more than 3 providers unless the homeowner asks to try another.
8. IF the homeowner says stop THEN THE SYSTEM SHALL not start further calls.

### Requirement 8: Renovation talk-track

**User Story:** As a homeowner, I want a bathroom renovation handled with the drawings I already uploaded, so that contractors are quoting the real space.

#### Acceptance Criteria

1. WHEN the homeowner asks to renovate a room THEN THE SYSTEM SHALL pull that room’s drawings into the brief.
2. WHEN a contractor is on the call THEN THE SYSTEM SHALL describe the scope and that plans exist (and what they show, if the model can see them).
3. WHEN a quoted price is clearly above the stated budget THEN THE SYSTEM SHALL ask for a better number on that call or a follow-up call, citing only numbers this demo actually heard.
4. WHEN outreach is done THEN THE SYSTEM SHALL list quotes / notes side by side. It SHALL NOT book a contractor.

### Requirement 9: Visible agent work

**User Story:** As a judge or homeowner, I want to see what HomeOps is doing, so that the demo is not a black box.

#### Acceptance Criteria

1. WHEN HomeOps looks up a model, searches providers, or starts a call THEN THE SYSTEM SHALL show a short activity line (tool name + result).
2. WHEN a call finishes THEN THE SYSTEM SHALL show a summary of what the provider said.
3. IF a tool fails THEN THE SYSTEM SHALL show a human-readable error.

### Requirement 10: Demo fitness

**User Story:** As a builder at a hack night, I want this to run with Vite for the UI and uvicorn for the API, so that we can demo in one session.

#### Acceptance Criteria

1. THE SYSTEM SHALL run a React + Vite frontend and a FastAPI backend. Secrets come from environment variables, never from git.
2. WHILE the live session is open THEN THE SYSTEM SHALL be turn-taking (speech starts quickly after the user stops talking under a normal network).
3. WHEN a call is placed THEN THE SYSTEM SHALL show dialing state as soon as Guava accepts the call.
4. THE SYSTEM SHALL listen on `0.0.0.0` and `PORT` when a port is provided (local default 8000).
