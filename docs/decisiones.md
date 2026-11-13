# Decisiones de arquitectura (ADR)

Formato: contexto → decisión → consecuencias. Las decisiones se revisan al cerrar cada fase.

## ADR-001 · Parquet + DuckDB en la fase 0; PySpark a partir de la fase 1

- **Fecha:** 28/10/2026 · **Estado:** aceptada
- **Contexto:** el plan prevé PySpark en modo local para el procesado batch, pero permite Parquet + DuckDB
  cuando resuelvan mejor un paso intermedio, documentando el motivo. En Windows nativo, Spark necesita
  `winutils.exe`/`hadoop.dll` para escribir Parquet, binarios que no distribuye Apache y que habría que
  descargar de repositorios de terceros. Un mes de PLACSP cabe holgadamente en memoria.
- **Decisión:** silver y gold se construyen con `lxml` (parseo en streaming), `pyarrow` (esquemas
  explícitos) y DuckDB (deduplicación, particionado e indicadores en SQL).
- **Consecuencias:** el pipeline se ejecuta en el portátil sin servicios externos. Para el histórico
  completo (fase 1) se migrará la consolidación y los indicadores a PySpark ejecutado en Docker o WSL2;
  el SQL de `build_gold.py` es casi directamente portable a Spark SQL (`QUALIFY` y ventanas `RANGE`
  requieren reescritura). Spark aparecerá así en la memoria donde aporta: el volumen completo.

## ADR-002 · La aplicación no depende de Neo4j ni de Docker

- **Fecha:** 28/10/2026 · **Estado:** aceptada
- **Contexto:** Docker no está instalado en el portátil a fecha 28/10/2026. El explorador de grafo solo
  necesita subgrafos pequeños (organismo-empresa) que se obtienen agregando la tabla de contratos.
- **Decisión:** la API lee la capa gold (Parquet) con DuckDB embebido. Neo4j se reserva para lo que solo
  él aporta: algoritmos de Graph Data Science (indicadores 9-12, fase 3) y consultas Cypher. El
  `docker-compose.yml` define mongo, neo4j (con GDS), redis, api y frontend para cuando Docker esté
  disponible. Los CSV para Neo4j se generan y prueban (`export_neo4j.py`); la carga (`load_neo4j.py`)
  queda pendiente de verificar con Neo4j en marcha.
- **Consecuencias:** demo en directo sin dependencias frágiles. Hay que instalar Docker Desktop antes de
  la fase 3.

## ADR-003 · ECharts como única librería de visualización

- **Fecha:** 28/10/2026 · **Estado:** aceptada
- **Contexto:** el plan propone deck.gl/MapLibre (mapa), Sigma.js o react-force-graph (grafo) y D3 o
  ECharts (gráficos). Tres librerías implican tres modelos de interacción y de exportación.
- **Decisión:** Apache ECharts para gráficos, coropletas (GeoJSON registrado) y grafo con disposición por
  fuerzas, con renderizado SVG y botón de exportación en cada figura (requisito de la memoria).
- **Consecuencias:** un solo mapa base sin teselas (no depende de servicios externos de mapas). Si en la
  fase 2 hace falta mostrar subgrafos de miles de nodos, se valorará Sigma.js (WebGL).

## ADR-004 · Territorio = NUTS del lugar de ejecución

- **Fecha:** 28/10/2026 · **Estado:** aceptada (provisional)
- **Contexto:** cada licitación declara `RealizedLocation/CountrySubentityCode` con un código NUTS 2021
  (de nivel 1 a 3 según el caso). El organismo tiene dirección postal, pero no código INE.
- **Decisión:** el mapa agrega por NUTS 2 (comunidad autónoma) y NUTS 3 (provincia) del lugar de ejecución,
  con geometrías NUTS 2021 de Eurostat/GISCO. Canarias se desplaza junto a la península solo en la
  visualización. Los códigos de nivel 1 (p. ej. `ES5`) no se asignan a ninguna región.
- **Consecuencias:** el nivel municipio y la geocodificación del organismo (vía INE/IGN) quedan para la
  fase 1, como prevé el plan.

## ADR-005 · Claves de organismo y empresa

- **Fecha:** 28/10/2026 · **Estado:** aceptada (provisional, hasta la resolución de entidades)
- **Decisión:** organismo = `ID_PLATAFORMA` del órgano de contratación (más fino que el NIF, que comparten
  varios órganos de una misma administración), con respaldo en NIF y nombre. Empresa = NIF normalizado
  (mayúsculas, sin separadores ni prefijo `ES`), con respaldo `SIN-NIF:<nombre>`.
- **Consecuencias:** las UTE y los adjudicatarios extranjeros aparecen con identificadores no NIF; la
  unificación por reglas y similitud de cadenas se hará en la fase 1.

## ADR-006 · Una versión vigente por expediente

- **Fecha:** 28/10/2026 · **Estado:** aceptada
- **Contexto:** el feed publica una entrada nueva cada vez que cambia un expediente y anuncia las
  anulaciones como `at:deleted-entry`.
- **Decisión:** en silver se conserva la última versión por `(dataset, entry_id)` según `updated`, y se
  descartan las entradas eliminadas después de esa versión. Lotes y resultados se toman de esa versión.
- **Consecuencias:** silver refleja el estado más reciente; el historial completo sigue en raw.

## ADR-007 · Raw inmutable con manifiesto

- **Fecha:** 28/10/2026 · **Estado:** aceptada
- **Decisión:** los zip de PLACSP se guardan sin descomprimir en `data/raw/placsp/<dataset>/` y se
  registran en `manifest.jsonl` (URL, tamaño, SHA-256, `Last-Modified`, fecha de descarga). El parser
  lee directamente del zip. La descarga se repite solo si el hash no coincide.

## ADR-008 · Umbrales estadísticos donde no hay umbral legal

- **Fecha:** 28/10/2026 · **Estado:** aceptada
- **Decisión:** solo el fraccionamiento usa un umbral legal (art. 118.1 LCSP). Plazo corto, baja atípica
  y concentración se marcan por percentiles de la distribución observada, como hace la literatura de
  *red flags* (Fazekas et al., 2016). Todos los parámetros están en `pipelines/indicators/params.py`.
- **Consecuencias:** las alertas son relativas al conjunto de datos procesado y cambiarán al incorporar
  el histórico completo; se documenta en la memoria.

## ADR-009 · Versiones del frontend compatibles con Node 18

- **Fecha:** 28/10/2026 · **Estado:** aceptada
- **Contexto:** el portátil tiene Node 18.17.1. Las últimas versiones de Vite requieren Node 20.19+.
- **Decisión:** React 18.3, Vite 5.4, Tailwind 3.4, TypeScript 5.6 y ECharts 5.5, con versiones exactas.
  La imagen Docker del frontend usa Node 20.
- **Consecuencias:** al actualizar Node a 20 o superior se podrá subir de versión sin cambios de código.
