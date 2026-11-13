# Tareas del proyecto. Instalar just: `uv tool install rust-just` (o `winget install Casey.Just`).
# En Windows se usa PowerShell como intérprete.
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

periodo := "202609"

# Lista las tareas
default:
    @just --list

# Instala dependencias de Python y del frontend
setup:
    uv sync
    cd frontend; npm install

# Descarga un periodo (AAAA o AAAAMM) de licitaciones y contratos menores de PLACSP
ingest p=periodo:
    uv run python -m pipelines.ingest.placsp --dataset licitaciones --periodo {{p}}
    uv run python -m pipelines.ingest.placsp --dataset menores --periodo {{p}}

# raw -> silver (Parquet particionado por año)
silver:
    uv run python -m pipelines.transform.build_silver

# Informe de calidad de silver en docs/calidad/
calidad nombre="silver":
    uv run python -m pipelines.quality.report --nombre {{nombre}}

# silver -> gold (indicadores y agregados)
gold:
    uv run python -m pipelines.indicators.build_gold

# CSV para Neo4j y carga (requiere `docker compose up -d neo4j`)
neo4j:
    uv run python -m pipelines.graph.export_neo4j
    uv run python -m pipelines.graph.load_neo4j

# Geometrías NUTS para el mapa
geo:
    uv run python -m pipelines.reference.build_geo

# Pipeline completo para un periodo
pipeline p=periodo: (ingest p) silver calidad gold

# API en http://localhost:8000 (documentación en /docs)
api:
    uv run uvicorn api.main:app --reload

# Frontend en http://localhost:5173
web:
    cd frontend; npm run dev

# Tests, lint y tipos
test:
    uv run pytest

lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy
    cd frontend; npm run typecheck

# Servicios Docker (mongo, neo4j, redis)
up:
    docker compose up -d mongo neo4j redis

down:
    docker compose down
