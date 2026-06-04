# Local run (current scaffold)

## Docker

From repository root:

```bash
docker compose up --build -d
```

App URL:

- `http://127.0.0.1:8000/` (Kanban frontend, statically built and served by FastAPI)
- Health API: `http://127.0.0.1:8000/api/health`

Stop:

```bash
docker compose down
```

## Convenience scripts

- macOS: `./scripts/start-mac.sh` and `./scripts/stop-mac.sh`
- Linux: `./scripts/start-linux.sh` and `./scripts/stop-linux.sh`
- Windows: `scripts\start-pc.bat` and `scripts\stop-pc.bat`
