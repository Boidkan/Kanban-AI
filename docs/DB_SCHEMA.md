# Database schema proposal (Part 5)

This document proposes the SQLite schema and initialization approach for storing one Kanban board per user in the MVP, while keeping the model ready for multiple users.

## Goals

- Keep persistence simple for MVP.
- Store board state as JSON to avoid over-modeling card/column tables too early.
- Preserve a clean path to multi-user support.
- Make first-run database creation automatic and deterministic.

## Storage choice

- Engine: SQLite
- File: `backend/data/app.db` (created automatically if missing)
- Board payload format: JSON text serialized from frontend/backend board contract

## Proposed schema

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  board_json TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
```

## Why this structure

- `users.username` is unique for auth lookup and future expansion.
- `boards.user_id UNIQUE` enforces MVP rule: one board per user.
- `board_json` keeps card/column structure flexible while product behavior evolves.
- `version` enables optimistic concurrency later if needed.
- `created_at`/`updated_at` simplify audit/debug and future sync logic.

## JSON payload shape

`boards.board_json` stores the entire board object:

```json
{
  "columns": [
    { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"] }
  ],
  "cards": {
    "card-1": { "id": "card-1", "title": "Example", "details": "..." }
  }
}
```

This matches the existing `BoardData` structure in frontend code, minimizing translation logic.

## Initialization and migration strategy

On backend startup (or before first DB operation), run a deterministic bootstrap routine:

1. Ensure parent directory exists (`backend/data/`).
2. Open SQLite connection to `backend/data/app.db` (creates file automatically).
3. Execute `PRAGMA` statements.
4. Execute `CREATE TABLE IF NOT EXISTS` statements.
5. Seed default MVP user if missing:
   - `username = 'user'`
6. Seed default board row for that user if missing, using current initial Kanban JSON.

This approach is enough for MVP and can evolve into a lightweight migration table later (for example `schema_migrations`) once schema changes become frequent.

## Read/write behavior (for Part 6 implementation)

- Read board:
  - Resolve user by username
  - Fetch `boards.board_json` by `user_id`
  - Deserialize JSON into typed response model
- Write board:
  - Validate payload schema
  - Serialize JSON and update `boards.board_json`
  - Increment `version`
  - Update `updated_at = CURRENT_TIMESTAMP`

## Test plan for Part 6

- Schema creation on empty filesystem creates DB and tables.
- Bootstrap creates default user and board once (idempotent).
- JSON round-trip serialization/deserialization preserves board structure.
- Update path increments `version` and updates timestamp.
