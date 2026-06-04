FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend /frontend
RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN uv sync --project /app/backend --no-dev

COPY backend /app/backend
COPY --from=frontend-builder /frontend/out /app/frontend-out

EXPOSE 8000

CMD ["uv", "run", "--project", "/app/backend", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
