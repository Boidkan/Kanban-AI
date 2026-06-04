# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A full-stack Project Management MVP: a Kanban board with an AI chat sidebar. A **Next.js** frontend is built to static assets and served by a **FastAPI** backend, which persists board state in **SQLite** and calls an LLM API for the AI features. Everything is packaged into a single Docker container. Auth is multi-user with open self-signup; a default `user` / `password` account is seeded for convenience. Passwords are hashed with argon2.

## Commands

Run the app (Docker, from repo root):
```bash
./scripts/start-mac.sh        # also: start-linux.sh, start-pc.bat
./scripts/stop-mac.sh
```
App at http://127.0.0.1:8000, health at `/api/health`. The scripts just delegate to `docker compose`.

Smoke-test the Dockerized app end-to-end (builds, starts, hits live endpoints, always tears down):
```bash
./scripts/test-docker.sh                  # includes a live OpenAI connectivity call
RUN_AI_TEST=0 ./scripts/test-docker.sh    # skip the AI call (no key / offline)
```

Frontend (from `frontend/`):
```bash
npm run dev            # local dev server (NOT the Docker static-export flow)
npm run build          # static export to frontend/out (what Docker serves)
npm run lint           # eslint
npm run test:unit      # vitest (component + lib)
npm run test:e2e       # playwright (needs: npx playwright install)
npm run test:all       # unit then e2e
```
Run a single frontend test: `npx vitest run src/lib/kanban.test.ts` or `npx vitest run -t "test name"`.

Backend (from repo root — `PYTHONPATH` must include root so `backend` imports resolve):
```bash
PYTHONPATH=. pytest backend/tests
PYTHONPATH=. pytest backend/tests/test_db.py::test_name   # single test
```
Inside Docker, Python deps are managed with `uv` (`uv sync`, `uv run`), not pip.

## Architecture

**Static frontend served by backend.** `frontend/next.config.ts` sets `output: "export"`, so `npm run build` emits static files to `frontend/out`. The Dockerfile is multi-stage: build frontend → copy `out` into the Python image at `/app/frontend-out`. In `backend/main.py`, the catch-all `GET /{full_path:path}` route serves those files with SPA fallback to `index.html`. API routes are all under `/api/...` and take precedence.

**Session auth (DB-backed, multi-user).** `POST /api/auth/login` looks the user up in SQLite and verifies the password with argon2 (`backend/auth.py`), returning a bearer token; the backend stores `token -> username` in an in-memory dict (resets on restart). `POST /api/auth/register` is open self-signup: it validates the username (3-32 chars, `[A-Za-z0-9_-]`) and password (>= 8), rejects a taken username with 409, creates the user with a hashed password + a freshly seeded board, and logs them straight in. The default `user` / `password` account is seeded (hashed) at startup. The `get_current_username` dependency reads `Authorization: Bearer <token>` and gates all data/AI routes — `GET/PUT /api/board`, `POST /api/ai/board`, `POST /api/ai/connectivity` — returning 401 without a valid token. The authenticated username comes from the session, not the URL (routes have no `{username}` path param). The frontend stores the token in `localStorage` (`pm-auth-token`) via `frontend/src/lib/api.ts`, which attaches it to every request; `POST /api/auth/logout` revokes it. `KanbanApp.tsx` has login/create-account modes. Public routes: `/api/health`, `/api/auth/login`, `/api/auth/register`, and the static frontend.

**Board is a single JSON blob per user.** `db.py` stores the entire board (`{columns, cards}`) as a JSON string in the `boards.board_json` column, one row per user, with a `version` integer that increments on every update. There is no per-card/per-column SQL modeling. `BoardModel` (in `main.py`) is the validation contract and enforces **referential integrity** (every `cardIds` entry maps to a card, every card is referenced exactly once, `card.id` matches its key) — invalid boards are rejected (422 on PUT, 502 on an AI update). Writes use optimistic concurrency: PUT accepts `expected_version` and returns **409** on mismatch. The canonical seed lives only in `backend/db.py` `default_board_payload()`; `frontend/src/lib/kanban.ts` exports just a `fallbackBoard` skeleton used when the board can't be loaded.

**DB bootstrap.** `initialize_database()` runs once at app startup (in `create_app`). It creates the schema if missing, seeds the default `user` + board, and migrates any legacy `"Example task"` seed data (`is_legacy_example_board`) to the current default. The repository read/write functions no longer re-init per call. SQLite lives at `backend/data/app.db` (gitignored; the container initializes its own clean copy and it is not persisted across container recreation).

**AI chat flow** (`POST /api/ai/board`): backend loads the current board, sends `question + conversation history + board JSON` to the LLM (`backend/ai.py`) using an OpenAI structured-output `json_schema` response format. The model returns `{assistant_response, board_update}`. If `board_update` is non-null, it is merged into the current board (`_merge_board_update`), re-validated against `BoardModel`, persisted with `expected_version` (version bumps), and the new board is returned with `board_updated: true`. The frontend (`KanbanBoard`) then refreshes from the returned board — board updates flow through this single path; the browser never parses freeform AI text.

**Frontend state.** `KanbanApp.tsx` handles the login/logout gate via the backend session API. `KanbanBoard.tsx` owns board state and dnd-kit drag handlers; all HTTP goes through `frontend/src/lib/api.ts` (`login`, `logout`, `fetchBoard`, `saveBoard`, `chatWithAI`). It tracks the board version (in a ref) for optimistic-concurrency saves, debounces per-keystroke column renames, and on any save failure re-fetches from the server so local state never diverges. Domain logic (card-move algorithm, ID generation, types) lives in `src/lib/kanban.ts`, kept separate from UI components.

## Important discrepancy: AI provider

The root `AGENTS.md` specifies OpenRouter with model `openai/gpt-oss-120b` and `OPENROUTER_API_KEY`, but it is **stale**. The actual implementation in `backend/ai.py` calls `https://api.openai.com/v1/chat/completions` directly with model `gpt-4o-mini` and reads `OPENAI_API_KEY` — and `docs/PLAN.md` Part 8 confirms OpenAI + `gpt-4o-mini` was the intended design. Treat the code + PLAN.md as source of truth. The `.env` file at repo root (loaded by `docker-compose.yml`) must define `OPENAI_API_KEY`.

## Conventions

These come from `AGENTS.md` / `frontend/AGENTS.md` and the existing code:
- Keep it simple. No over-engineering, no unnecessary defensive programming, no features beyond the current scope.
- When debugging, find the root cause with evidence before fixing — do not guess.
- No emojis, ever. Keep docs minimal.
- Use the CSS color tokens (`--accent-yellow`, `--primary-blue`, `--secondary-purple`, `--navy-dark`, `--gray-text`) defined in `globals.css`, not ad-hoc colors.
- Tests rely on stable `data-testid` selectors and stable IDs; when changing user-visible behavior, update both unit/component and e2e tests.
- Shared domain logic goes in `src/lib/`; UI orchestration stays in components.
- Project planning docs live in `docs/` (see `docs/PLAN.md`).
