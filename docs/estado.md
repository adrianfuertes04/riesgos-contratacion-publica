# Estado del proyecto

Fotografía a **28/10/2026** (fase 0, semana 1). Qué está hecho, qué falta según el plan y qué hay que
mejorar. Se actualiza al cerrar cada fase; el detalle de cada día está en [bitacora.md](bitacora.md).

Leyenda: ✅ hecho y probado con datos reales · 🧪 hecho y probado solo con tests · ⚠️ escrito pero
sin probar · ❌ falta.

## Cómo arrancarlo

Siempre desde la carpeta del proyecto, cada comando en su terminal:

```powershell
cd C:\Users\adrian.fuertes\Downloads\prueba-proyecto
uv run uvicorn api.main:app --reload
```

```powershell
cd C:\Users\adrian.fuertes\Downloads\prueba-proyecto\frontend
npm run dev
```

Web en http://localhost:5173 y documentación de la API en http://localhost:8000/docs.

---

## 1. Qué está hecho

### Datos (capa 1)

| Componente | Estado | Notas |
|---|---|---|
| Ingesta PLACSP (`pipelines/ingest/placsp.py`) | ✅ | Idempotente, manifiesto con SHA-256. Descargado 09/2026 de licitaciones y menores |
| Parser CODICE → silver (`pipelines/transform/`) | ✅ | 163.533 entradas en ~90 s; esquema explícito; deduplicación; particionado por año |
| Informe de calidad (`pipelines/quality/`) | ✅ | Nulos, duplicados, NIF, rangos y reglas. Resultado en `docs/calidad/` |
| Validación de NIF (DNI, NIE, CIF) | ✅ | Comprobada con NIF reales de PLACSP |
| Listas de códigos CODICE oficiales | ✅ | Procedimiento, tipo de contrato, órgano, urgencia, resultado, anuncio, CPV… |
| Indicadores I1-I8 y puntuaciones (`pipelines/indicators/`) | ✅ | 82.769 contratos, 25.901 alertas |
| CSV para Neo4j (`pipelines/graph/export_neo4j.py`) | ✅ | Organismos, empresas, licitaciones, lotes y relaciones |
| Geometrías NUTS 2 y 3 para el mapa | ✅ | Eurostat/GISCO, Canarias desplazada |

### Aplicación

| Componente | Estado | Notas |
|---|---|---|
| API FastAPI (`api/`) | ✅ | 14 rutas, todas responden en < 0,1 s con datos reales |
| Pantalla de inicio (KPIs, evolución, sectores, top) | ✅ | |
| Mapa por comunidad y provincia con selector de indicador | ✅ | Ficha del territorio al pulsar |
| Explorador de grafo con filtros y panel lateral | ✅ | Subgrafos de 1 o 2 saltos |
| Fichas de organismo y de empresa | ✅ | Semáforo de indicadores, contrapartes, alertas y contratos |
| Panel de alertas filtrable, ordenable y paginado | ✅ | Enlace al anuncio original en PLACSP |
| Aviso de "indicadores, no pruebas" | ✅ | Visible en todas las pantallas |
| Exportación de gráficos a SVG | ✅ | Botón en cada figura |

### Calidad y documentación

| Componente | Estado | Notas |
|---|---|---|
| Tests (`tests/`) | ✅ | 40 tests: parser, NIF/seudonimización, ingesta con reintentos/Range, indicadores, pipeline y API |
| ruff, mypy, TypeScript | ✅ | Sin errores |
| CI (`.github/workflows/ci.yml`) | 🧪 | Workflow de GitHub Actions para backend y frontend |
| `CLAUDE.md`, `README.md` | ✅ | |
| `docs/fuentes.md`, `indicadores.md`, `decisiones.md`, `bitacora.md` | ✅ | Con cifras reales |
| `docs/propuesta_tfm.md` | 🧪 | Borrador; se completa en febrero |
| Notebook de exploración (`notebooks/01_inventario_calidad.py`) | ✅ | Formato *percent* |

### Docker y sin probar

| Componente | Estado | Notas |
|---|---|---|
| `docker-compose.yml` y `Dockerfile` (API y frontend) | ✅ | `.dockerignore` añadidos; imágenes construidas y probadas en `http://localhost:8080` |
| Carga en Neo4j (`pipelines/graph/load_neo4j.py`) y `queries.cypher` | ⚠️ | Falta levantar `neo4j` en Docker y probar la carga y consultas |
| `justfile` | ⚠️ | `just` no está instalado (`uv tool install rust-just`) |
| Hooks de pre-commit | ⚠️ | No activados (`uv run pre-commit install`, requiere un commit) |

---

## 2. Qué falta (según el plan)

### Fase 0 (nov 2026 - feb 2027)

- ❌ **Probar Neo4j en Docker** (`docker compose up -d neo4j`, carga con `load_neo4j.py` y consultas Cypher).
- ❌ **Descargar el histórico completo** de licitaciones (643), menores (1143) y plataformas
  autonómicas (1044). Son varios GB a ~0,2 MB/s: lanzarlo de noche.
- ❌ **Estadísticas básicas en PySpark** sobre el histórico (ADR-001: Spark en Docker o WSL2).
- ❌ **Ollama**: probar la extracción sobre 20 pliegos y elegir modelo (semanas 7-9).
- ❌ **Explorar el BORME** con un mes de PDF y comprobar que se puede parsear (semanas 7-9).
- ❌ **Prototipo de grafo en Neo4j** con un año de datos y 3-4 consultas Cypher (semanas 10-12).
- ❌ **Propuesta de TFM** de 3-5 páginas para el director (semanas 10-12).
- ❌ **Commit inicial** del repositorio (está inicializado, sin commits).

### Fase 1 (núcleo de datos)

- ❌ Pipeline completo raw → silver en PySpark, particionado por año, con tests de calidad.
- ❌ Resolución de entidades: unificar empresas (UTE, NIF extranjeros, adjudicatarios sin NIF) por
  reglas y similitud de cadenas.
- ❌ Geocodificación de organismos a municipio/provincia/CCAA (INE/IGN) y nivel municipio en el mapa.
- ❌ Carga del grafo completo en Neo4j (`neo4j-admin database import`).

### Capas 2, 3 y 4

| Capa | Qué hay | Qué falta |
|---|---|---|
| 2 · BORME | Esqueleto `pipelines/ingest/borme.py` | Verificar la fuente, parsear PDF, vincular empresa-persona, indicadores 10-12 |
| 3 · LLM sobre pliegos | Esquema Pydantic (`pipelines/llm/schemas.py`) y borrador de prompt | Descarga de pliegos, extracción con Ollama, conjunto de oro anotado, evaluación frente a API, indicadores 13-14, vista de pliego en la app |
| 4 · Extensiones | Nada | Embeddings, explicaciones con LLM, Isolation Forest, Kafka (opcional) |
| Grafo avanzado | Proyección GDS de ejemplo en `queries.cypher` | Indicador 9 (PageRank, betweenness, Louvain) |

---

## 3. Qué necesita mejora

Ordenado por importancia para la memoria.

### Prioridad alta

1. **Personas físicas como adjudicatarias.** 4.051 adjudicatarios se identifican con DNI y nombre.
   La app los muestra y permite buscarlos. Ya existe el flag `--anonimizar-personas` en `build_gold.py`
   para seudonimizarlos (`PF-<hash>`); falta decidir con el director la política definitiva y
   regenerar `data/gold/` si se publica o entrega con ella activa. Sección 10 del plan.
2. **I6 · Precio anómalo es demasiado ruidoso.** Incluso limitado a procedimientos con concurrencia,
   el 27 % de los contratos abiertos se adjudica al ≥ 99,9 % del presupuesto. Probablemente son
   contratos por precios unitarios en los que se publica el máximo como importe. Hay que identificarlos
   antes de usar I6 en la memoria.
3. **Sesgo territorial del mapa.** Sin la sindicación 1044 faltan las comunidades con plataforma
   propia. No sacar conclusiones territoriales hasta incorporarla.
4. **Un mes no es representativo.** El fichero mensual contiene los cambios del mes (adjudicaciones de
   2016 a 2026), no los contratos del mes. Los percentiles (I2, I5, I6) y las puntuaciones cambiarán al
   cargar el histórico.

### Prioridad media

5. **I3 · Fraccionamiento:** con un solo mes la ventana de 365 días queda truncada. Contrastar el
   criterio (grupo CPV de 3 dígitos, 365 días) con los informes de la OIReScon.
6. **I8 · Recurrencia:** necesita varios años de datos para ser útil.
7. **Umbrales legales:** verificar en el BOE las fechas exactas de vigencia de los umbrales del contrato
   menor (LCSP y TRLCSP).
8. **Referencias de los indicadores:** revisar los informes de la OIReScon y de la CNMC y completar
   `docs/indicadores.md`.
9. ✅ **Descarga con reintentos y reanudación (`placsp.py`)** implementada y probada con tests.
10. ✅ **Ranking de empresas por riesgo:** `/api/companies?sort=risk_score` exige ahora un mínimo de
    contratos (`MIN_CONTRACTS_COMPANY = 10`), igual que `/api/buyers`.

### Prioridad baja

11. ✅ **Tamaño del frontend:** ECharts se importa por módulos (`echarts/core`) y se separa en chunks
    en `vite.config.ts` (bundle total reducido de 1,23 MB a ~876 kB en 3 chunks).
12. **Redis** está en el `docker-compose.yml` pero la API no lo usa; con datos de un mes no hace falta.
13. **MongoDB:** `pymongo` está instalado para la capa 3, pero aún no se usa.
14. **Node 18:** obliga a versiones antiguas de Vite y Tailwind (ADR-009). Al pasar a Node 20 o
    superior se pueden actualizar.
15. **Aviso de deprecación de `httpx`** en el cliente de pruebas de Starlette: está silenciado en
    `pyproject.toml`; revisar al actualizar FastAPI.
16. **Accesibilidad y móvil:** la interfaz se ha revisado en escritorio y en un panel estrecho, pero
    no se ha auditado la accesibilidad.
17. ✅ **Integración continua:** añadido `.github/workflows/ci.yml` para ejecutar `ruff`, `mypy`,
    `pytest`, `tsc` y `vite build` en cada push o pull request.

---

## 4. Archivos auxiliares

- `.claude/launch.json`: configuración para previsualizar la app desde Claude Code. Se puede borrar
  sin afectar al proyecto.
