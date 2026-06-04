# Authentication implementation plan

This document is the detailed execution plan for replacing the single hardcoded
login with real, database-backed accounts and open self-signup. It is structured
like `docs/PLAN.md`: per-part implementation checklists, a three-way test split,
success criteria, and a phase gate at the end of every part.

## Starting point

Session-token auth already exists (added during the security remediation):

- `POST /api/auth/login` validates credentials and returns a bearer token.
- `POST /api/auth/logout` revokes the token.
- An in-memory `token -> username` session store and a `get_current_username`
  dependency gate all data/AI routes (401 without a valid token).
- The frontend stores the token in `localStorage` (`pm-auth-token`) and attaches
  it to every request (`frontend/src/lib/api.ts`).

What does **not** exist yet, and is the scope of this plan:

- Passwords are not stored. `login` checks two hardcoded constants
  (`AUTH_USERNAME` / `AUTH_PASSWORD`) instead of the database.
- There is no way to create a second account, and no sign-up UI.

## Decisions (signed off)

- **Signup model:** open self-signup. Anyone can create an account from the UI.
- **Password hashing:** a dedicated library. Use **argon2-cffi** (OWASP's first
  recommendation; ships manylinux wheels so no compiler is needed in the
  `python:3.12-slim` image). `bcrypt` is an acceptable drop-in if preferred.
- **Existing account:** keep the default `user` / `password` account seeded (now
  with a stored hash) so current logins, tests, and docs keep working.
- **Account fields:** username + password only. No email or display name.

## Conventions

Per `AGENTS.md`: keep it simple, no over-engineering, root-cause fixes, no emojis,
minimal docs. Passwords must never be logged, returned in any response, or stored
in plaintext. Login failures return a single generic 401 (do not reveal whether
the username exists). Tests use stable `data-testid` selectors; behavior changes
update unit/component and e2e tests together.

### Testing split used throughout

- **Backend unit tests:** hashing utility, auth routes, schema/migration, DB.
- **Frontend unit/component tests:** auth screen, form validation, mode toggle.
- **Frontend integration/e2e tests:** register -> board -> logout -> re-login.

### Global phase-gate rule

- [ ] At the end of each part, pause and ask the user for approval before
  starting the next part.

## Part 1 - Plan and sign-off

### Implementation checklist

- [ ] Capture the decisions above and keep this file as the source of truth for
  the auth work.
- [ ] Confirm scope: self-signup, argon2 hashing, keep seeded `user`, username +
  password only.
- [ ] Present the plan and request approval to proceed to Part 2.

### Tests for Part 1

- [ ] Manual review that each part has actionable checklists and success criteria.

### Success criteria for Part 1

- [ ] User approves the plan before any code changes begin.

## Part 2 - Password hashing utility

### Implementation checklist

- [ ] Add `argon2-cffi` to `backend/pyproject.toml` dependencies; run `uv sync`
  and confirm it resolves in the Docker build (`python:3.12-slim`, wheels only).
- [ ] Add `backend/auth.py` (or a section of `db.py`) with two small functions:
  - `hash_password(password: str) -> str`
  - `verify_password(password: str, password_hash: str) -> bool` (returns False on
    a malformed/invalid hash rather than raising).
- [ ] Use argon2 defaults via a module-level `PasswordHasher`; do not expose tuning
  knobs (keep it simple).
- [ ] Never log or print the password or the hash.

### Tests for Part 2

- **Backend unit tests**
  - [ ] `hash_password` produces a verifiable hash; the same password hashes to
    different values (random salt) but both verify.
  - [ ] `verify_password` returns True for the right password, False for the wrong
    password, and False for a malformed hash string.
- **Frontend unit/component tests** — none (backend-only part).
- **Frontend integration/e2e tests** — none.

### Success criteria for Part 2

- [ ] Hashing utility works locally and inside the Docker image.
- [ ] No plaintext password is ever persisted or logged.

## Part 3 - Database schema: store password hashes

### Implementation checklist

- [ ] Add a `password_hash TEXT` column to the `users` table in `SCHEMA_SQL`.
- [ ] Add an idempotent migration in `initialize_database()` for existing DBs:
  inspect `PRAGMA table_info(users)` and `ALTER TABLE users ADD COLUMN
  password_hash TEXT` only if the column is missing.
- [ ] Update the default seed so the `user` account is created with
  `password_hash = hash_password("password")`; backfill the hash if an existing
  `user` row has a NULL/empty `password_hash`.
- [ ] Extend `create_user_with_board(...)` to accept and persist a
  `password_hash`, so account creation and board seeding stay in one place.
- [ ] Add a repository helper `get_user_auth(username) -> (id, password_hash) |
  None` for the login path, and `username_exists(username) -> bool` for
  registration.

### Tests for Part 3

- **Backend unit tests**
  - [ ] Fresh init creates the `users` table with a `password_hash` column and a
    seeded `user` whose stored hash verifies against `"password"`.
  - [ ] Migration test: initialize a DB without the column (legacy shape), run
    `initialize_database()`, and assert the column now exists and the `user`
    hash is backfilled.
  - [ ] `create_user_with_board` persists the provided hash and seeds a board;
    `get_user_auth` / `username_exists` behave correctly for present/absent users.
- **Frontend unit/component tests** — none.
- **Frontend integration/e2e tests** — none.

### Success criteria for Part 3

- [ ] Schema supports per-user password hashes.
- [ ] Existing databases migrate cleanly with no data loss; the seeded `user`
  remains loginable.

## Part 4 - Backend login against the database

### Implementation checklist

- [ ] Change `POST /api/auth/login` to look up the user via `get_user_auth` and
  verify with `verify_password`, instead of comparing the hardcoded constants.
- [ ] Remove `AUTH_USERNAME` / `AUTH_PASSWORD` from the login path (the values
  live only as the seeded default account in `db.py` now).
- [ ] Return a single generic 401 for both unknown username and wrong password.
- [ ] Keep the rest of the session flow unchanged (token issue, in-memory store,
  `get_current_username`, logout).

### Tests for Part 4

- **Backend unit tests**
  - [ ] Seeded `user` / `password` still logs in and receives a token.
  - [ ] Wrong password -> 401; unknown username -> 401; both with the same detail
    message.
  - [ ] A token from a successful login still authorizes `GET /api/board`.
- **Frontend unit/component tests** — none (contract unchanged for login).
- **Frontend integration/e2e tests**
  - [ ] Existing login regression (sign in -> board) still passes.

### Success criteria for Part 4

- [ ] Login is fully DB-backed; the hardcoded credential check is gone.
- [ ] No regression to existing authenticated routes.

## Part 5 - Backend registration endpoint (self-signup)

### Implementation checklist

- [ ] Add `POST /api/auth/register` accepting `{username, password}` as a Pydantic
  model with validation:
  - username: trimmed, non-empty, length 3-32, allowed characters (letters,
    digits, `_`, `-`); reject otherwise with 422.
  - password: minimum length 8; reject otherwise with 422.
- [ ] Reject a duplicate username with **409** (via `username_exists`).
- [ ] On success: hash the password, `create_user_with_board(...)` (creates the
  user with the hash and seeds a fresh board), then issue a session token and
  return `{token, username}` so the client is logged in immediately.
- [ ] Registration is a public route (like login); it must not require a token.
- [ ] Never echo the password back; never include the hash in the response.

### Tests for Part 5

- **Backend unit tests**
  - [ ] Register a new user -> 200 with a token; the token authorizes
    `GET /api/board` and returns a freshly seeded board at version 1.
  - [ ] Registering an existing username (e.g. `user`) -> 409.
  - [ ] Invalid username and short password each -> 422.
  - [ ] The newly registered user can subsequently log in via `/api/auth/login`.
  - [ ] Two different accounts have independent boards (editing one does not
    change the other).
- **Frontend unit/component tests** — none yet (UI is Part 6).
- **Frontend integration/e2e tests** — none yet.

### Success criteria for Part 5

- [ ] New accounts can be created via the API and get their own board.
- [ ] Validation and duplicate handling return correct status codes.

## Part 6 - Frontend: account creation UI

### Implementation checklist

- [ ] Add `register(username, password)` to `frontend/src/lib/api.ts` mirroring
  `login` (POST `/api/auth/register`, store the returned token on success, surface
  the server error message on failure).
- [ ] Update `KanbanApp.tsx` to support two modes on the auth screen: "Sign in"
  and "Create account", toggled by a link/button. Reuse the existing styling and
  CSS tokens; add a `data-testid` toggle and stable labels.
- [ ] Create-account mode: username + password fields (plus a client-side check
  that mirrors the server rules: username 3-32 allowed chars, password >= 8) with
  clear inline validation and a submit button.
- [ ] On successful register, transition straight into the board (same path as a
  successful login). On failure (409 duplicate, 422 invalid) show the server's
  message in the existing `role="alert"` element.
- [ ] Keep login as the default mode; do not change the logout flow.

### Tests for Part 6

- **Backend unit tests** — none (no backend change).
- **Frontend unit/component tests**
  - [ ] Toggling between Sign in and Create account swaps the heading/button.
  - [ ] Submitting create-account calls `register` with the entered values and, on
    success, renders the board.
  - [ ] Duplicate-username error and validation errors render in the alert and do
    not navigate to the board.
  - [ ] Client-side validation blocks an obviously invalid submission (short
    password) before calling the API.
- **Frontend integration/e2e tests** — covered in Part 7.

### Success criteria for Part 6

- [ ] A user can create an account entirely from the UI and land on their board.
- [ ] Login and create-account modes are both reachable and clearly distinct.

## Part 7 - End-to-end tests, docs, and regression

### Implementation checklist

- [ ] Add a Playwright flow: open the app, switch to Create account, register a
  brand-new username, confirm the board renders, log out, then log back in with
  the same credentials.
- [ ] Add a Playwright assertion that registering a taken username shows the
  duplicate error and stays on the auth screen. (Mock the backend responses in the
  e2e harness as the existing specs do.)
- [ ] Update `./scripts/test-docker.sh` to also exercise `POST /api/auth/register`
  with a unique username against the live container and confirm the issued token
  works on `GET /api/board`.
- [ ] Update docs: `README.md` (sign-up walkthrough), `CLAUDE.md` (auth section:
  DB-backed login + registration), and the root `AGENTS.md` note that auth is now
  multi-user with self-signup.
- [ ] Run the full suite: backend pytest, frontend unit, frontend e2e, and the
  Docker smoke test. Pause for final approval.

### Tests for Part 7

- **Backend unit tests**
  - [ ] Keep all auth/board tests green with the new flow.
- **Frontend unit/component tests**
  - [ ] Keep Part 6 component tests green.
- **Frontend integration/e2e tests**
  - [ ] Register -> board -> logout -> re-login passes.
  - [ ] Duplicate-username registration shows an error and does not log in.
  - [ ] Existing login + core Kanban regression still passes.

### Success criteria for Part 7

- [ ] Self-signup works end-to-end in the running app, verified by automated tests
  and the Docker smoke test.
- [ ] All suites pass; docs reflect the new auth model.

## Out of scope (future work)

These are intentionally excluded to keep the change focused; note them so they are
not assumed to be done:

- Password reset / change-password flow and email (no email field is stored).
- Rate limiting / lockout on login and registration (brute-force protection).
- Roles, permissions, or admin user management.
- Persisting sessions across backend restarts (sessions remain in-memory).
- CAPTCHA or other anti-abuse measures on open signup.
