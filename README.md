# Riesgos en la contratación pública española

Trabajo Fin de Máster: sistema de **big data + IA + visual analytics** sobre los datos abiertos de la
Plataforma de Contratación del Sector Público (PLACSP). Ingesta el histórico de licitaciones, lo limpia
en capas (raw → silver → gold), calcula indicadores de riesgo basados en la literatura y los muestra en
una aplicación web con panel nacional, mapa, explorador de grafo, fichas y panel de alertas.

> **Aviso.** Los indicadores son señales estadísticas de riesgo calculadas sobre datos abiertos. No
> constituyen prueba ni acusación de irregularidad alguna.

## Estado

Fase 0 (exploración), 28/10/2026. La capa 1 funciona de extremo a extremo con un mes real de PLACSP;
las capas 2 (BORME) y 3 (LLM) solo tienen esquemas y esqueletos. Qué está hecho, qué falta y qué hay
que mejorar en [docs/estado.md](docs/estado.md); diario de trabajo en [docs/bitacora.md](docs/bitacora.md).

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 automáticamente)
- Node.js 18 o superior
- Opcional: Docker Desktop (MongoDB, Neo4j, Redis) y [just](https://github.com/casey/just)
  (`uv tool install rust-just`)

## Puesta en marcha (Windows, PowerShell)

```powershell
uv sync
cd frontend; npm install; cd ..

# 1. Descargar un mes de licitaciones y de contratos menores (idempotente)
uv run python -m pipelines.ingest.placsp --dataset licitaciones --periodo 202609
uv run python -m pipelines.ingest.placsp --dataset menores --periodo 202609

# 2. raw -> silver, informe de calidad y gold
uv run python -m pipelines.transform.build_silver
uv run python -m pipelines.quality.report --nombre 202609
uv run python -m pipelines.indicators.build_gold

# 3. API (http://localhost:8000/docs) y web (http://localhost:5173), en dos terminales
uv run uvicorn api.main:app --reload
cd frontend; npm run dev
```

Con `just` instalado: `just pipeline 202609`, `just api`, `just web`, `just test`.

Opcional, con Docker: `docker compose up -d neo4j` y después
`uv run python -m pipelines.graph.export_neo4j` y `uv run python -m pipelines.graph.load_neo4j`.
`docker compose up -d --build` levanta además la API y la web en http://localhost:8080.

## Arquitectura

```
PLACSP (zip con Atom/CODICE) ──► data/raw/placsp/  (inmutable, manifiesto con SHA-256)
                                   │  pipelines/transform  (lxml + pyarrow, esquemas explícitos)
                                   ▼
                                 data/silver/  tenders · lots · awards  (Parquet, particionado por año)
                                   │  pipelines/indicators  (DuckDB SQL)
                                   ▼
                                 data/gold/  contracts · buyers · companies · pairs · alerts · territories…
                                   │                          │
                       api/ (FastAPI + DuckDB)      pipelines/graph → Neo4j (GDS, fase 3)
                                   │
                       frontend/ (React + Vite + Tailwind + ECharts)
```

Decisiones y su motivo en [docs/decisiones.md](docs/decisiones.md); fuentes verificadas en
[docs/fuentes.md](docs/fuentes.md); definición de cada indicador en [docs/indicadores.md](docs/indicadores.md).

## Estructura

```
prueba-proyecto/
├── CLAUDE.md                 resumen del plan y convenciones
├── docs/                     fuentes, indicadores, bitácora, decisiones, propuesta, calidad/
├── data/                     raw/ silver/ gold/ samples/ (no se versiona salvo muestras)
├── pipelines/
│   ├── ingest/               placsp.py (+ borme.py, pliegos.py: capas 2-3)
│   ├── transform/            parser CODICE y construcción de silver
│   ├── quality/              NIF e informe de calidad
│   ├── indicators/           parámetros e indicadores I1-I8
│   ├── graph/                CSV y carga en Neo4j, consultas Cypher
│   ├── llm/                  esquema de extracción de pliegos (capa 3)
│   └── reference/            listas de códigos CODICE y geometrías NUTS
├── api/                      FastAPI
├── frontend/                 React + Vite
├── notebooks/                exploración (formato percent)
├── tests/                    pytest
├── docker-compose.yml, Dockerfile, justfile, pyproject.toml, uv.lock
```

## Calidad

```powershell
uv run pytest
uv run ruff check . ; uv run ruff format --check . ; uv run mypy
cd frontend; npm run typecheck
uv run pre-commit install   # hooks locales con ruff, mypy y pytest
```

## Datos y licencias

Código bajo licencia MIT. Los datos proceden de fuentes abiertas del sector público y conservan su
licencia de origen (ver [docs/fuentes.md](docs/fuentes.md)). Límites administrativos © EuroGeographics.
