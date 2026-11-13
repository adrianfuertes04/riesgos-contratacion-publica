# CLAUDE.md — TFM: análisis visual y detección de riesgos en la contratación pública española

Resumen del plan de proyecto (Adrián Fuertes López, Máster en Análisis y Visualización de Datos Masivos,
UNIR, edición octubre 2026) y convenciones para trabajar en este repositorio.

## Reglas que no se negocian

- Proyecto personal y académico: **nunca** usar datos, credenciales, servidores ni APIs de la empresa
  del autor. Solo datos abiertos y recursos propios.
- Trabajar **por fases y por capas**: no empezar una extensión hasta que el núcleo de la fase actual
  funcione de extremo a extremo con datos reales.
- Antes de implementar una fuente de datos, verificar que la URL/API sigue vigente y documentarlo en
  `docs/fuentes.md` (fecha, formato, licencia, volumen).
- Cada fase termina con código funcionando, tests mínimos, validación con cifras reales y una entrada
  en `docs/bitacora.md`.
- **No inventar cifras, umbrales legales ni indicadores.** Cada regla de negocio cita su fuente en
  `docs/indicadores.md`; las elecciones metodológicas se marcan como tales en
  `pipelines/indicators/params.py`.
- Las alertas son indicadores de riesgo, no pruebas de irregularidad. El aviso debe verse en la app.
- Preferir soluciones simples. Spark, Neo4j y MongoDB se usan donde aportan; si Parquet + DuckDB
  resuelve mejor un paso, se usa y se documenta en `docs/decisiones.md`.

## Idioma

Identificadores de código en inglés; comentarios, documentación, interfaz y memoria en español.

## Capas

1. **Núcleo (obligatoria):** PLACSP → Parquet, limpieza, grafo, indicadores 1-8, app web, memoria.
2. **BORME (muy deseable):** administradores, vínculos empresa-persona, indicadores 10-12.
3. **LLM sobre pliegos (deseable):** extracción con Ollama + evaluación frente a API y anotación manual.
4. **Extensiones (opcional):** embeddings, explicaciones con LLM, anomalías no supervisadas, Kafka.

Regla de corte: si el 1/6/2027 la capa 1 y la app no están completas, se cancelan las capas 3-4.

## Estado actual (28/10/2026, fase 0)

Detalle completo en `docs/estado.md` (hecho / falta / mejoras); mantenerlo al día al cerrar cada fase.

- Hecho: estructura, ingesta idempotente de PLACSP, parser CODICE → silver, informe de calidad,
  indicadores I1-I8 en gold, CSV para Neo4j, API FastAPI y frontend con las 5 pantallas mínimas.
  Probado de extremo a extremo con septiembre de 2026 real (82.769 contratos; cifras en la bitácora).
- Decisión abierta: tratamiento de adjudicatarios personas físicas (4.051 con DNI) — ver bitácora.
- Pendiente fase 0: histórico completo, PySpark (ADR-001), Docker y Neo4j (ADR-002), Ollama, BORME.
- Capas 2-3: solo esquemas y esqueletos (`pipelines/ingest/borme.py`, `pipelines/llm/`).

## Mapa del código

| Ruta | Qué hace |
|---|---|
| `pipelines/ingest/placsp.py` | Descarga zip de PLACSP a `data/raw/placsp/` con manifiesto y SHA-256 |
| `pipelines/transform/codice.py` | Parser del Atom/CODICE (tenders, lots, awards, deleted) |
| `pipelines/transform/build_silver.py` | raw → staging → silver deduplicado y particionado por año |
| `pipelines/quality/` | Validación de NIF e informe de calidad (`docs/calidad/`) |
| `pipelines/indicators/` | Parámetros e indicadores I1-I8 → `data/gold/*.parquet` |
| `pipelines/graph/` | CSV y carga en Neo4j, consultas Cypher |
| `pipelines/reference/` | Listas de códigos CODICE oficiales y geometrías NUTS |
| `api/` | FastAPI sobre gold con DuckDB |
| `frontend/` | React + Vite + TS + Tailwind + ECharts |

## Comandos

```
uv sync                                   # dependencias Python (3.12)
uv run python -m pipelines.ingest.placsp --dataset licitaciones --periodo 202609
uv run python -m pipelines.transform.build_silver
uv run python -m pipelines.quality.report
uv run python -m pipelines.indicators.build_gold
uv run uvicorn api.main:app --reload      # API en :8000
cd frontend && npm run dev                # web en :5173
uv run pytest && uv run ruff check . && uv run mypy
```

## Entorno

Portátil MSI Pulse 16, 32 GB RAM, RTX 4070 Laptop (8 GB VRAM), Windows. Todo debe ejecutarse ahí.
A 28/10/2026 hay Python 3.12 (uv), Node 18.17 y Java 11; no hay Docker ni `just`.
