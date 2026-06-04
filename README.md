# Kanban-AI MVP

This repository contains a full-stack Project Management MVP with a Kanban board and an AI assistant sidebar. This projext was vibe coded and unverified for production.

It is designed to run locally in Docker, with:

- a **Next.js frontend** (UI)
- a **FastAPI backend** (API + static hosting)
- a **SQLite database** (persistent board data per user, inside container storage)
- an **OpenAI integration** for AI chat-based board updates

---

## Who this guide is for

This README is written for complete beginners in frontend or backend development.

You do not need prior full-stack experience to follow it. If you can run terminal commands, you can run and test this app.

---

## What the app does

- Lets a user sign in with MVP credentials (currently harded coded on front end):
  - username: `user`
  - password: `password`
- Shows a Kanban board with editable columns and draggable cards
- Saves board changes through backend APIs into SQLite
- Includes an AI chat sidebar:
  - user asks a question
  - backend sends board context + conversation to OpenAI
  - AI returns structured output
  - backend may persist board updates automatically

---

## Technology summary

### Frontend

- **Next.js 16** + **React 19** + **TypeScript**
- **Tailwind CSS** for styling
- **dnd-kit** for drag-and-drop

### Backend

- **Python FastAPI**
- **Pydantic** models for request/response validation
- **httpx** for calling OpenAI API

### Database

- **SQLite**
- Stores one board per user as JSON (`board_json`)

### Testing

- **Vitest + Testing Library** for frontend unit/component tests
- **Playwright** for frontend integration/e2e tests
- **pytest** for backend tests

### Runtime / packaging

- **Docker + Docker Compose**
- Multi-stage Docker build (build frontend static assets, then serve from backend)

---

## High-level architecture

1. Browser loads `/` from FastAPI.
2. FastAPI serves static frontend files.
3. Frontend calls backend APIs (`/api/board/...`, `/api/ai/...`).
4. Backend reads/writes SQLite.
5. Backend optionally calls OpenAI for AI chat requests.
6. Backend returns validated JSON response to frontend.
7. Frontend updates UI state.

---

## What was implemented (Parts 1-10)

1. **Plan + docs**: detailed execution plan and working docs.
2. **Scaffolding**: Docker, backend skeleton, run scripts.
3. **Static frontend serving**: Next.js static build served by FastAPI.
4. **MVP auth gate**: frontend sign-in/logout with hardcoded credentials.
5. **DB modeling**: SQLite schema + JSON board strategy.
6. **Backend board APIs**: fetch/update board per user, DB initialization.
7. **Frontend-backend integration**: board loads/saves via API.
8. **AI connectivity**: OpenAI connectivity endpoint with deterministic `2+2`.
9. **Structured AI backend flow**: AI returns structured response + optional board update.
10. **AI sidebar UI**: full chat panel integrated into board with auto-refresh on AI updates.

---

## Prerequisites

Install these tools:

- Docker Desktop (running)
- Node.js + npm (for local frontend tests)
- Python 3 (for local backend tests)

Check versions:

```bash
docker --version
node --version
npm --version
python3 --version
```

---

## Environment setup

Create a root `.env` file:

```bash
OPENAI_API_KEY=your_openai_key_here
```

This key is used by backend AI endpoints and is loaded by `docker-compose.yml`.

---

## Run the app

From repo root:

```bash
./scripts/start-mac.sh
```

Open:

- App: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Health API: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

Stop:

```bash
./scripts/stop-mac.sh
```

Linux/Windows scripts are also available in `scripts/`.

---

## First walkthrough (beginner-friendly)

1. Start the app.
2. Go to `http://127.0.0.1:8000`.
3. Sign in:
   - `user`
   - `password`
4. Try core board actions:
   - rename a column
   - add a card
   - drag a card to another column
5. Refresh browser:
   - confirm changes persisted
6. Open AI chat sidebar:
   - ask a question like:
     - `Summarize this board`
     - `Move one backlog task to done`
7. Observe:
   - assistant response appears in sidebar
   - board updates automatically when AI returns `board_update`

---

## API walkthrough

### Get board for user

```bash
curl -s http://127.0.0.1:8000/api/board/user | python3 -m json.tool
```

### Update board for user

```bash
curl -s -X PUT http://127.0.0.1:8000/api/board/user \
  -H "Content-Type: application/json" \
  -d '{"board":{"columns":[],"cards":{}}}'
```

(Use valid board schema; invalid schema returns `422`.)

### AI connectivity check

```bash
curl -s -X POST http://127.0.0.1:8000/api/ai/connectivity | python3 -m json.tool
```

### AI board chat

```bash
curl -s -X POST http://127.0.0.1:8000/api/ai/board/user \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize the board","conversation":[]}' | python3 -m json.tool
```

---

## Run tests

### Frontend unit/component tests

```bash
cd frontend
npm run test:unit
```

### Frontend integration/e2e tests

```bash
cd frontend
npm run test:e2e
```

### Backend tests

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pytest httpx
PYTHONPATH=. pytest backend/tests
```

---

## Data and persistence notes

- Board data is persisted in SQLite while the container is running.
- The default seed data now uses **unique cards matching Parts 1-10** of the implementation plan.
- Legacy generic `"Example task"` seed data is migrated to the newer defaults during backend initialization.

---

## Troubleshooting

### Docker daemon not running

Start Docker Desktop and retry `./scripts/start-mac.sh`.

### AI endpoint returns key error

Ensure `.env` exists at repo root with:

```bash
OPENAI_API_KEY=...
```

Then restart the app.

### Playwright browser issues

From `frontend/`:

```bash
npx playwright install
```

---

## Directory map

- `frontend/` - Next.js UI
- `backend/` - FastAPI app + DB logic + tests
- `docs/` - project docs and plan
- `scripts/` - start/stop scripts
- `Dockerfile`, `docker-compose.yml` - container build/run config

---

## Next improvements (optional)

- Move auth from hardcoded frontend logic to backend/DB-backed auth.
- Persist SQLite data across full container recreation with a Docker volume.
- Add role-based permissions and audit trail for AI board updates.
