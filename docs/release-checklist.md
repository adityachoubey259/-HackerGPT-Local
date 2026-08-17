# Release Checklist

## Release Status

Current candidate: `1.0.0-rc.1`.

Final `1.0.0` should be stamped only after all blocking acceptance gates pass, including host-side
visual acceptance, real provider smoke testing, native launcher acceptance, and real local training
verification on target hardware.

## Required Checks

- Run all backend and frontend quality gates from `docs/test-matrix.md`.
- Confirm Alembic reports `0006_local_auth (head)`.
- Run `python scripts\benchmark.py --iterations 3 --json-output data\benchmarks\phase15-16-baseline.json --markdown-output docs\performance-baseline.md`.
- Confirm `scripts/hackergpt.py start` creates a pre-migration backup unless explicitly disabled.
- Confirm `config/policy.yaml` remains the central security boundary.
- Confirm local provider failures do not silently fall back to cloud providers.
- Confirm the browser calls only HackerGPT backend APIs.
- Confirm optional `transformers-peft` preflight reports backend dependency and hardware status honestly.
- Confirm a real local training smoke can launch with local model files, write adapter artifacts,
  calculate checksums, evaluate, promote, reject/delete, and roll back.
- Confirm worker cancellation and interrupted-job recovery are visible in Learning Studio.

## Versioning

- Python package metadata uses PEP 440 form `1.0.0rc1`.
- Runtime API/UI version reports SemVer form `1.0.0-rc.1`.
- Frontend package metadata reports `1.0.0-rc.1`.

## Migration Plan

Phase 15/16 adds file-backed evaluation runs and learning/model-registry metadata under `data/`.
The RC closure auth pass adds `0006_local_auth`. Runtime preferences use the existing `settings`
table.

The native launcher backs up local data and config before migrations during `start`.

## Dependency Plan

No large ML, CUDA, ROCm, vector database, or model runtime dependencies are added to the core app.

Optional real training dependencies are available through `pip install -e ".[training]"`.
The FastAPI app launches training through an explicit subprocess worker only after preflight and
user action; it does not execute fine-tuning inline.

## Compatibility

- Python: `>=3.12,<3.14`
- Frontend: Node/npm compatible with the checked-in Vite 7 toolchain
- Database: SQLite initially through SQLAlchemy repositories with PostgreSQL portability preserved
- Operating systems: Windows-first scripts with cross-platform Python backend assumptions
