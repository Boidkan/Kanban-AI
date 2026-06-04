## Backend overview

The backend is a FastAPI service in `backend/`.

Current scope for scaffolding:

- Serves the statically built Next.js frontend at `/` with SPA fallback to `index.html`.
- Exposes a health API endpoint at `/api/health`.
- Exposes board APIs:
  - `GET /api/board/{username}`
  - `PUT /api/board/{username}`
- Exposes AI connectivity API:
  - `POST /api/ai/connectivity`
  - Runs a deterministic `2+2` prompt through OpenAI using model `gpt-4o-mini`.
- Exposes structured AI board chat API:
  - `POST /api/ai/board/{username}`
  - Sends question + conversation + board JSON to OpenAI and returns assistant message plus optional persisted board update.
- Serves static asset files directly from the built frontend output directory.
- Uses `uv` for dependency management inside the Docker image via `backend/pyproject.toml`.
- Uses SQLite persistence in `backend/data/app.db` with initialization + repository helpers in `backend/db.py`.

Core files:

- `backend/main.py`: FastAPI app, API route, and frontend static/fallback serving logic.
- `backend/ai.py`: OpenAI client helper for connectivity checks.
- `backend/db.py`: Database schema/bootstrap and board repository operations.
- `backend/pyproject.toml`: Python project metadata and dependencies.
- `backend/tests/test_app.py`: Route tests for health, frontend serving, and board APIs.
- `backend/tests/test_ai.py`: OpenAI request builder/response error tests.
- `backend/tests/test_db.py`: Repository and initialization unit tests.

Future parts will replace the temporary root page with the built frontend and add persistent data + AI routes.