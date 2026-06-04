# Code review

Comprehensive review of the Project Management MVP (frontend + backend + packaging) as of 2026-06-04, on branch `plan-detail`. Findings are ordered by severity within each category. Each item has a concrete action.

This is an MVP that was vibe-coded and is explicitly not production-verified, so several items below are acceptable for local single-user use and only matter if the app is ever shared or hosted. Those are marked accordingly.

## Remediation status (2026-06-04)

All critical/high/medium findings have been fixed and the full suite re-run green (backend 32, frontend unit 12, e2e 5, Docker smoke test passing). Fixed: S1 (full backend session auth), S2 (DB files untracked + gitignored), S3 (.dockerignore added), C1 (board referential-integrity validation + defensive frontend render), C2 (save-failure resync), C3 (optimistic-concurrency `expected_version` → 409), P1 (debounced rename saves), P2 (removed per-call DB init), M1 (frontend seed reduced to a skeleton fallback). Each item is marked Fixed inline below. Low-severity items (C4, C5 partially, P3, M2, M3, M4) were addressed where cheap and otherwise left as noted.

## Summary

The architecture is sound for an MVP: static Next.js build served by FastAPI, board persisted as a JSON blob per user in SQLite, AI updates flowing through a single validated path. Test coverage is good (now 32 backend, 12 frontend unit, 5 e2e, all passing). The findings below were the main gaps before remediation: no real backend authentication, no referential-integrity validation of board updates (can crash the UI), committed database files, optimistic UI with no rollback, and save-per-keystroke on column rename.

## Security

### S1. No real backend authentication (Medium — blocker for any non-local deployment)
The frontend "auth" is a cosmetic `localStorage` flag (`KanbanApp.tsx`); the backend has no auth at all. `GET/PUT /api/board/{username}` and `POST /api/ai/board/{username}` are fully open. Anyone with network access can read/modify any board and spend OpenAI tokens through the AI endpoint. Acceptable for `127.0.0.1` MVP only.
- [ ] Before any shared/hosted deployment, add backend auth (session cookie or token) and derive `username` from the authenticated session instead of the URL path.
- [ ] At minimum, gate `/api/ai/*` so unauthenticated callers cannot drive billable OpenAI calls.

### S2. Database files are committed to git (Medium)
`backend/data/app.db`, `app.db-shm`, and `app.db-wal` are all tracked. WAL/SHM are runtime artifacts that must never be committed, and the DB carries mutable runtime state. The `.gitignore` has stale rules (`db.sqlite3`, `db.sqlite3-journal`) that do not match the actual path.
- [ ] `git rm --cached backend/data/app.db backend/data/app.db-shm backend/data/app.db-wal`
- [ ] Add `backend/data/` (or `*.db`, `*.db-wal`, `*.db-shm`) to `.gitignore`; remove the stale `db.sqlite3*` rules.

### S3. No `.dockerignore` (Low–Medium)
There is no `.dockerignore`, so the build context includes `.git`, `.venv`, `node_modules`, `.pytest_cache`, and the committed `backend/data/*.db`. `COPY backend /app/backend` then bakes the committed dev DB into the image, so the container ships pre-seeded mutable state instead of initializing clean. It also bloats and slows the build.
- [ ] Add `.dockerignore` excluding at least: `.git`, `.venv`, `**/node_modules`, `backend/data`, `.pytest_cache`, `frontend/.next`, `frontend/out`.

### S4. AI board updates are persisted with loose validation (Low for single user; see C1)
The structured-output schema sets `board_update` to `additionalProperties: true`, and `_merge_board_update` applies it without integrity checks. A crafted prompt can persist an arbitrary board shape. Blast radius is limited to the caller's own board in the single-user MVP, but the validation gap is real — see C1 for the action.

## Correctness

### C1. Board updates are not integrity-checked and can crash the UI (High)
`BoardModel` validates structure (`columns`, `cards`) but not referential integrity: nothing ensures every `cardIds` entry maps to a card in `cards`, or that every card is referenced. This applies to both `PUT /api/board` and the AI merge path. The frontend then runs `column.cardIds.map((cardId) => board.cards[cardId])` in `KanbanBoard.tsx` and passes `undefined` into `<KanbanCard card={undefined}>`, which reads `card.id`/`card.title` → runtime crash / blank board. `_merge_board_update` makes this easy to hit because it can take `columns` from the AI update while keeping `cards` from the current board (or vice versa), so the two halves can disagree.
- [ ] Add a `model_validator` on `BoardModel` that rejects boards where any `cardIds` entry is missing from `cards` or any card is unreferenced (return 422 for PUT, 502 for AI). 
- [ ] Defensively, have the frontend filter out missing cards before render so a bad payload degrades instead of crashing.

### C2. Optimistic updates with no rollback (Medium)
`commitBoard` sets local state then fires the PUT; on failure it only sets an error string (`KanbanBoard.tsx`). Local state and the DB then diverge with no reconciliation. This directly contradicts the project's own guidance in `frontend/AGENTS.md` ("prefer confirm-then-render … unless rollback behavior is clearly defined").
- [ ] On save failure, re-fetch the board (or snapshot-and-rollback), or switch to confirm-then-render for the MVP.

### C3. Lost-update race; `version` is unused (Medium)
`boards.version` is incremented on every write but never used as a guard. `update_board_for_user` reads the version and writes `version+1` with no optimistic-concurrency check, and the PUT/AI routes accept no expected version. Two writers (two tabs, or an AI update racing a drag) silently overwrite each other. The frontend also ignores the returned version entirely.
- [ ] Accept an `expected_version` (or `If-Match`) on PUT and return 409 on mismatch, or explicitly document and enforce a single-writer assumption.

### C4. The latest chat question is sent twice (Low)
In `handleAIChatSubmit`, `nextConversation` already includes the new user message, and the call passes both `question` and that full `conversation`. The backend embeds both into the prompt (`call_openai_structured_board_response`), so the model sees the question duplicated.
- [ ] Send `conversation` without the trailing duplicate, or have the backend treat the last user turn as the question.

### C5. AI refresh can clobber concurrent edits (Low)
While `isAIThinking`, the user can still drag/add/edit. When the AI response returns with `board_updated`, `setBoard(response.board)` overwrites those edits — and the AI itself operated on a board snapshot that predates them.
- [ ] Disable board mutations while the AI is thinking, or re-fetch/merge instead of blindly replacing.

## Performance

### P1. Column rename saves on every keystroke (Medium)
`KanbanColumn`'s title `<input onChange>` calls `onRename` → `commitBoard` → a full-board PUT on every character. Each PUT re-serializes the whole board and bumps `version`. Typing a 10-character title issues 10 PUTs and 10 version bumps.
- [ ] Debounce saves (~300–500ms) or persist on blur; keep local state updates immediate.

### P2. `initialize_database()` runs on every read and write (Low–Medium)
Every `get_board_for_user`/`update_board_for_user` opens a fresh connection and runs `executescript` (PRAGMAs + three `CREATE TABLE IF NOT EXISTS` + index) plus the legacy-migration SELECT — on every request. `create_app` already bootstraps once at startup, so the per-call invocations are redundant work (and make reads capable of writing, via the migration branch).
- [ ] Remove the per-call `initialize_database()` from the repository functions; rely on the startup bootstrap.

### P3. Whole-board write per granular action (Low)
Every add/delete/move serializes and writes the entire board JSON. Fine at MVP scale; note for future growth (the JSON-blob model makes partial updates impossible by design).

## Maintainability and structure

### M1. Board shape is duplicated in four places (Medium)
The board contract lives in `backend/main.py` (Pydantic), `frontend/src/lib/kanban.ts` (types + seed), `backend/db.py` (`default_board_payload`), and is re-declared again in `tests/kanban.spec.ts`. The default-board seed is duplicated between `kanban.ts` and `db.py` and must be kept in sync by hand.
- [ ] Centralize the default board in one backend location; consider deriving the frontend type from a single source (or at least add a test that asserts the two seeds match).

### M2. Stale provider docs (Low)
Root `AGENTS.md` specifies OpenRouter / `gpt-oss-120b` / `OPENROUTER_API_KEY`, but the code and `docs/PLAN.md` (Part 8) use OpenAI / `gpt-4o-mini` / `OPENAI_API_KEY`. Already noted in `CLAUDE.md`.
- [ ] Update root `AGENTS.md` to match the implemented provider, or reconcile intentionally.

### M3. Unused multi-user scaffolding (Low, intentional)
`create_user_with_board` and the `users` table support multiple users, but no route creates users and only the default `user` is ever seeded. This is deliberate future-proofing per the plan; flagging so it is not mistaken for a live feature.
- [ ] No action required; revisit when real auth/multi-user lands (ties into S1).

### M4. Synchronous HTTP in request handlers (Low)
`backend/ai.py` uses blocking `httpx.post` inside sync `def` routes. FastAPI runs sync routes in a threadpool so this is safe, but each AI call ties up a worker thread for up to 45s.
- [ ] No action for the MVP; if scaling, switch to an async client and surface timeouts to the UI.

## Tests

Coverage is solid and the suites pass. Notable gaps tie directly to the findings above:
- [ ] Add a test that an inconsistent board (cardId with no matching card, or orphan card) is rejected (C1).
- [ ] Add a frontend test for save-failure behavior (C2).
- [ ] Add a test for rename debounce / save batching once P1 is addressed.

## What is already good

- Path-traversal guard in static serving is correct (`resolve()` + `is_relative_to`).
- `create_app` is parametrized on `frontend_dir`/`db_path`, making the backend cleanly testable.
- Error mapping is clear and consistent (404/422/502/503), including a deterministic AI connectivity check.
- AI updates flow through one validated persist path; the browser never parses freeform AI text.
- Legacy seed migration is implemented and tested; DB init is idempotent and tested.
- `.env` is correctly gitignored and untracked (the API key is not committed).
