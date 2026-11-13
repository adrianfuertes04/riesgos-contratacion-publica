# Imagen de la API (FastAPI + DuckDB sobre la capa gold montada en /data).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY pipelines ./pipelines
COPY api ./api

ENV TFM_DATA_DIR=/data
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
