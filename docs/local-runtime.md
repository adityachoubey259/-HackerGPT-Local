# Native Local Runtime

Phase 14 adds a native stdlib launcher at `scripts/hackergpt.py`.

## Commands

```powershell
python scripts/hackergpt.py doctor
python scripts/hackergpt.py start
python scripts/hackergpt.py status
python scripts/hackergpt.py stop
python scripts/hackergpt.py backup
python scripts/hackergpt.py restore .\data\backups\backup.zip
```

Windows one-click wrappers:

```powershell
scripts\start-hackergpt.cmd
scripts\stop-hackergpt.cmd
```

## Startup

`start` resolves the repository from the script path, runs Alembic migrations, starts Uvicorn on localhost by default, writes a launcher-owned PID file, logs to `data/logs/hackergpt.log`, and waits with bounded probes.

It serves the production frontend from `frontend/dist` through FastAPI when `HACKERGPT_SERVE_FRONTEND=true`. Build the frontend with `npm.cmd run build` before production local startup.

## Safety

- The launcher never downloads models.
- `stop` only targets the PID recorded by this launcher.
- `restore` rejects archive entries outside `data/databases/`, `data/knowledge/`, and `config/`.
- The default host is `127.0.0.1`.
- Probes are bounded and should not be used to compensate for isolated workspace networking.

## Docker

Docker Compose is optional. The `api` service serves the built frontend and uses a named data volume. Qdrant and SearxNG are available behind `qdrant` and `research` profiles.
