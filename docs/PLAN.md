# Project implementation plan

This document is the single detailed execution plan for Parts 1-10, including implementation checklists, test split, success criteria, and phase gates.

### Global phase-gate rule

- [ ] At the end of each part, pause and ask the user for approval before starting the next part.

### Testing split used throughout

- **Backend unit tests**: FastAPI routes, services, schema validation, DB behavior, AI client wrappers.
- **Frontend unit/component tests**: React components, utility functions, interaction handlers.
- **Frontend integration/e2e tests**: Browser-level flows with Playwright for key user journeys.

## Part 1 - Plan

### Implementation checklist

- [x] Keep this file as the single source of truth for the project plan.
- [x] Define per-part checklists for implementation, tests, and success criteria.
- [x] Create `frontend/AGENTS.md` documenting the current frontend architecture and conventions.
- [x] Include guidance in `frontend/AGENTS.md` for future backend and AI integration work.
- [x] Present Part 1 output to the user and request explicit approval to proceed to Part 2.

### Tests for Part 1

- [x] Manual review that all ten parts now have concrete checklists and success criteria.
- [x] Manual review that `frontend/AGENTS.md` exists and matches current code structure.

### Success criteria for Part 1

- [x] `docs/PLAN.md` contains detailed, actionable checklists for Parts 1-10.
- [x] `frontend/AGENTS.md` is present and useful for future contributors/agents.
- [x] User approves the plan changes before Part 2 begins.

## Part 2 - Scaffolding

### Implementation checklist

- [x] Add backend scaffold in `backend/` with FastAPI app entrypoint.
- [x] Add Docker setup for running backend + serving static frontend artifacts.
- [x] Add cross-platform start/stop scripts in `scripts/` (macOS, Linux, Windows).
- [x] Implement a simple backend API route (for example `/api/health`).
- [x] Serve a temporary static hello-world page from FastAPI at `/` to verify wiring.
- [x] Document local run flow briefly in README/docs.
- [ ] Pause for user approval before Part 3.

### Tests for Part 2

- **Backend unit tests**
  - [x] Health route returns expected payload and status.
  - [x] FastAPI app startup/shutdown smoke test.
- **Frontend unit/component tests**
  - [ ] None required in this part unless temporary frontend code is introduced.
- **Frontend integration/e2e tests**
  - [x] Browser test that `/` serves the hello-world page.
  - [x] Browser/API test that hello-world page can call backend route.

### Success criteria for Part 2

- [x] `docker build` and container startup work locally.
- [x] Visiting `/` shows hello-world page served by backend.
- [x] Backend API route is reachable from the running app.

## Part 3 - Add in Frontend

### Implementation checklist

- [x] Build the existing Next.js frontend as static assets.
- [x] Configure FastAPI static serving so `/` renders the Kanban frontend.
- [x] Ensure frontend assets resolve correctly under container runtime.
- [x] Remove temporary hello-world page wiring from Part 2.
- [ ] Pause for user approval before Part 4.

### Tests for Part 3

- **Backend unit tests**
  - [x] Test static asset route/fallback handling in backend.
- **Frontend unit/component tests**
  - [x] Run and keep passing existing component + utility tests.
- **Frontend integration/e2e tests**
  - [x] Browser test that `/` shows the Kanban board after container startup.
    - Manual fallback accepted: start app, open `http://127.0.0.1:8000/`, confirm `Kanban Studio` heading and 5 columns render.
  - [x] Smoke test for static asset loading (JS/CSS served correctly).

### Success criteria for Part 3

- [x] Kanban board displays from backend-served static frontend at `/`.
- [x] Existing frontend tests pass.
- [x] Containerized app serves frontend reliably.

## Part 4 - Fake user sign-in experience

### Implementation checklist

- [x] Add login screen shown before board access.
- [x] Implement hardcoded credential check (`user` / `password`) for MVP.
- [x] Persist authenticated session state for active browser session.
- [x] Add logout action returning user to login screen.
- [x] Protect board route so unauthenticated users cannot access board content.
- [ ] Pause for user approval before Part 5.

### Tests for Part 4

- **Backend unit tests**
  - [x] If backend participates in auth, test login/logout/session endpoints.
    - N/A for Part 4 implementation: auth gate is frontend-only in this phase.
- **Frontend unit/component tests**
  - [x] Login form validation and credential handling tests.
  - [x] Route/guard behavior tests for auth gating.
- **Frontend integration/e2e tests**
  - [x] User cannot access board without login.
  - [x] Successful login displays board.
  - [x] Logout returns to login and revokes access.

### Success criteria for Part 4

- [x] Only correct credentials allow access.
- [x] Login and logout flows behave consistently.
- [x] Board is hidden when unauthenticated.

## Part 5 - Database modeling

### Implementation checklist

- [x] Propose SQLite schema for users, board metadata, and board JSON state.
- [x] Keep one board per user for MVP while preserving multi-user structure.
- [x] Define migration/initialization strategy for creating DB if missing.
- [x] Document schema rationale in `docs/` and request user sign-off.
- [ ] Pause for user approval before Part 6.

### Tests for Part 5

- **Backend unit tests**
  - [x] Schema creation/initialization test for empty filesystem.
  - [x] Serialization/deserialization tests for board JSON payloads.
- **Frontend unit/component tests**
  - [x] None required unless frontend model contracts are added.
- **Frontend integration/e2e tests**
  - [x] None required in this planning/modeling step.

### Success criteria for Part 5

- [x] Schema and JSON storage approach are documented and approved by user.
- [x] DB bootstrap path is clear and testable.

## Part 6 - Backend

### Implementation checklist

- [x] Add API routes to fetch and update board state for authenticated user.
- [x] Implement service/repository layer for DB reads/writes.
- [x] Ensure DB file is auto-created and initialized if missing.
- [x] Validate API request/response shapes with typed schemas.
- [x] Add error handling for invalid payloads and missing board state.
- [ ] Pause for user approval before Part 7.

### Tests for Part 6

- **Backend unit tests**
  - [x] Route tests for read/update success and validation failures.
  - [x] Repository tests for create/read/update board records.
  - [x] Initialization test for missing DB file.
- **Frontend unit/component tests**
  - [x] None required in this backend-only step.
- **Frontend integration/e2e tests**
  - [x] Optional API contract smoke tests if a harness is present.
    - Covered via backend API route tests in `backend/tests/test_app.py`.

### Success criteria for Part 6

- [x] Backend can persist and return board JSON per user.
- [x] DB auto-creation works from clean state.
- [x] Backend tests pass with good coverage of core paths.

## Part 7 - Frontend + Backend

### Implementation checklist

- [x] Replace frontend in-memory board state source with backend API fetch.
- [x] Wire card add/edit/delete/move and column rename to backend persistence.
- [x] Add loading and basic error states for network operations.
- [x] Keep UI behavior consistent with existing demo interactions.
- [ ] Pause for user approval before Part 8.

### Tests for Part 7

- **Backend unit tests**
  - [x] Keep API tests passing with any contract updates.
- **Frontend unit/component tests**
  - [x] Board behavior tests using mocked API responses.
  - [x] Error/loading state tests.
- **Frontend integration/e2e tests**
  - [x] End-to-end CRUD and drag/drop persistence test.
  - [x] Reload test confirms state remains persisted.

### Success criteria for Part 7

- [x] Kanban operations persist via backend.
- [x] Refreshing the page keeps latest board state.
- [x] Frontend and backend test suites pass.

## Part 8 - AI connectivity

### Implementation checklist

- [ ] Add backend OpenRouter client configuration using `.env` key.
- [ ] Use model `openai/gpt-oss-120b` exactly as specified.
- [ ] Add a simple backend AI route for connectivity verification.
- [ ] Implement deterministic "2+2" connectivity check path.
- [ ] Pause for user approval before Part 9.

### Tests for Part 8

- **Backend unit tests**
  - [ ] AI client request builder test (headers, model, payload).
  - [ ] Route behavior tests with mocked OpenRouter responses.
- **Frontend unit/component tests**
  - [ ] None required in this backend connectivity step.
- **Frontend integration/e2e tests**
  - [ ] Optional local smoke test for AI route when key is present.

### Success criteria for Part 8

- [ ] Backend can successfully call OpenRouter with configured model.
- [ ] "2+2" test path confirms end-to-end connectivity.

## Part 9 - Structured outputs for board updates

### Implementation checklist

- [ ] Define structured output schema containing assistant message and optional board update.
- [ ] Send board JSON + user question + conversation history to model.
- [ ] Validate and parse model output before applying updates.
- [ ] Apply optional board updates transactionally in backend.
- [ ] Return both assistant response and resulting board state to frontend.
- [ ] Pause for user approval before Part 10.

### Tests for Part 9

- **Backend unit tests**
  - [ ] Schema validation tests for valid/invalid model output.
  - [ ] Service tests for "message only" vs "message + board update".
  - [ ] Persistence tests ensuring updates are applied correctly.
- **Frontend unit/component tests**
  - [ ] None required until UI wiring in Part 10.
- **Frontend integration/e2e tests**
  - [ ] Optional API-level integration test with mocked model provider.

### Success criteria for Part 9

- [ ] Backend consistently returns validated structured responses.
- [ ] Optional board updates are safely persisted when present.
- [ ] Invalid model output is handled gracefully.

## Part 10 - AI sidebar in UI

### Implementation checklist

- [ ] Add sidebar chat UI integrated into existing Kanban layout.
- [ ] Send user prompts and conversation history to backend AI endpoint.
- [ ] Render assistant responses in chat thread.
- [ ] When backend returns board updates, refresh board state in UI automatically.
- [ ] Provide clear loading and error feedback in chat interaction.
- [ ] Run full regression tests and pause for final user approval.

### Tests for Part 10

- **Backend unit tests**
  - [ ] Keep AI and board update endpoint tests passing with UI contract.
- **Frontend unit/component tests**
  - [ ] Chat input/thread rendering tests.
  - [ ] Board refresh behavior test when update payload is returned.
- **Frontend integration/e2e tests**
  - [ ] Full chat flow test with mocked AI response.
  - [ ] Test where AI response updates board and UI reflects changes.
  - [ ] Regression smoke for login + core Kanban interactions.

### Success criteria for Part 10

- [ ] Sidebar chat works end-to-end with backend.
- [ ] AI-triggered board updates appear in UI without manual refresh.
- [ ] Comprehensive tests pass across frontend and backend.