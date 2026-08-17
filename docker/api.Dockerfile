FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY backend ./backend
COPY config ./config
COPY frontend/dist ./frontend/dist
COPY scripts ./scripts
RUN python -m pip install --no-cache-dir .
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn backend.api.app:create_app --factory --host 0.0.0.0 --port 8000"]
