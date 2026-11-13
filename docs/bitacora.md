# Bitácora

Diario de trabajo: fecha, qué se hizo, qué se aprendió y qué se decidió. Alimenta la memoria del TFM.

## 28/10/2026 · Fase 0, semana 1 — repositorio y pipeline mínimo de extremo a extremo

### Qué se hizo

- Estructura del repositorio según la sección 12 del plan, con `uv` (Python 3.12), ruff, mypy, pytest,
  pre-commit, `docker-compose.yml` (mongo, neo4j con GDS, redis, api, frontend) y `justfile`.
- Verificación de fuentes con peticiones reales (ver `docs/fuentes.md`): sindicaciones 643
  (licitaciones), 1143 (contratos menores) y 1044 (plataformas agregadas), listas de códigos CODICE y
  geometrías NUTS de GISCO.
- Ingesta idempotente con manifiesto y SHA-256 (`pipelines/ingest/placsp.py`). Descargado septiembre
  de 2026: licitaciones (302,9 MB comprimidos, 2,93 GB de XML en 193 ficheros Atom, 28 minutos) y
  contratos menores (36,9 MB).
- Parser CODICE → silver con esquema explícito, deduplicación por versión y particionado por año.
- Informe de calidad automático (`docs/calidad/calidad_202609.md`).
- Indicadores I1-I8 en gold, puntuaciones de contrato, organismo y empresa, y CSV para Neo4j.
- API FastAPI y frontend con las cinco pantallas mínimas (inicio, mapa, grafo, fichas, alertas).
- 37 tests (parser con un fixture real, NIF, ingesta, cada indicador con datos sintéticos, pipeline
  completo y API).

### Cifras reales (septiembre de 2026)

| Paso | Licitaciones | Menores | Total |
|---|---:|---:|---:|
| Entradas en el feed | 95.910 | 67.623 | 163.533 |
| Entradas anuladas (`deleted-entry`) | 218 | 112 | 330 |
| Expedientes tras deduplicar (silver) | 42.154 | 46.554 | 88.708 |
| Contratos adjudicados (gold) | 36.126 | 46.643 | 82.769 |
| Importe adjudicado sin IVA | 19.848,6 M€ | 215,3 M€ | 20.063,9 M€ |

- Tiempos en el portátil: parseo de licitaciones 50 s, menores 37 s, consolidación 3 s, gold 2,5 s.
  La API responde en menos de 0,1 s en todas las rutas.
- 5.377 órganos de contratación (1.539 con 10 o más contratos, que son los que reciben puntuación) y
  36.547 empresas adjudicatarias.
- Tasas por indicador sobre los casos aplicables: I1 único licitador 31,7 % de los abiertos; I3
  posible fraccionamiento 4,1 % de los menores; I4 poco competitivo 10,5 %; I5 plazo corto 3,7 %;
  I6 precio anómalo 27,1 %; I7 modificados 9,6 %. Alertas: 25.901 en total (I1 9.310, I2 77, I3 961,
  I4 3.784, I5 999, I6 7.266, I7 3.458, I8 46).
- El 86,6 % de los contratos tiene NUTS 3 de ejecución y el 95,6 % al menos NUTS 2.

### Qué se aprendió

1. **Un fichero mensual no son "los contratos del mes", sino los cambios del mes.** El zip de
   septiembre contiene expedientes cuya adjudicación va de 2016 a 2026; solo 29.309 contratos tienen
   fecha de referencia en septiembre de 2026. Para el histórico hay que procesar todos los ficheros y
   deduplicar globalmente, que es lo que ya hace `build_silver.py` (ADR-006).
2. **Fecha de publicación.** Los procedimientos sin anuncio de licitación (negociado sin publicidad,
   restringido, derivados de acuerdo marco) no tienen `DOC_CN`. La primera versión tomaba la primera
   fecha de cualquier anuncio, lo que producía 4.194 plazos negativos. Ahora el plazo se mide solo
   desde `DOC_CN` y la primera fecha de cualquier anuncio se guarda aparte (`first_notice_date`):
   quedan 217 plazos negativos, que se excluyen de I5.
3. **Resultados con 0 ofertas** (2.226) son prácticamente todos desiertos (código 3). Ningún
   resultado adjudicado tiene 0 ofertas.
4. **Fechas imposibles:** 9 adjudicaciones con año 0023, 0026, 1969… Se usan las fechas de anuncio en
   su lugar (`MIN_VALID_DATE`).
5. **Precio al 100 % del presupuesto (I6).** En la primera versión marcaba el 33,6 % de los contratos.
   En negociados sin publicidad el 76,8 % y en derivados de acuerdo marco el 75,1 % se adjudican al
   100 %, donde el ratio no es informativo: I6 se limita ahora a procedimientos con concurrencia en
   precio. Aun así, en abiertos el 27,3 % se adjudica al ≥ 99,9 %. Con una sola oferta ocurre en el
   43,4 % de los casos frente al 15,0 % con dos o más, coherente con la literatura de precio relativo,
   pero probablemente incluye contratos por precios unitarios en los que se publica el presupuesto
   máximo como importe. **Pendiente:** identificar esos contratos antes de usar I6 en la memoria.
6. **NIF de adjudicatarios.** De 36.545 identificadores distintos, 31.085 son NIF válidos; de los 5.459
   inválidos, 5.416 no tienen formato de NIF (identificadores extranjeros, de UTE…), así que los
   errores reales de dígito de control son muy pocos. **4.051 adjudicatarios se identifican con DNI**:
   son personas físicas, con nombre y DNI en los datos abiertos.
7. **Representatividad territorial.** La sindicación 643 no incluye las plataformas autonómicas
   (sindicación 1044). El mapa infrarrepresenta las comunidades con plataforma propia; hay que
   incorporar la 1044 antes de sacar conclusiones territoriales.
8. **Descarga lenta** (~0,15-0,2 MB/s) y sin `Content-Length`: el histórico completo (anuales de varios
   GB) llevará horas; conviene lanzarlo de noche y con reintentos.

### Decisiones

ADR-001 a ADR-009 en `docs/decisiones.md`: DuckDB en la fase 0 y Spark en la fase 1; la app no depende
de Docker ni de Neo4j; ECharts como única librería de visualización; territorio por NUTS de ejecución;
claves de organismo y empresa; una versión vigente por expediente; raw inmutable; umbrales estadísticos
donde no hay legal; versiones de frontend compatibles con Node 18.

### Pendiente

- Decidir con el director cómo tratar a los adjudicatarios personas físicas (DNI y nombre) en la
  aplicación y en el repositorio público (sección 10 del plan).
- Instalar Docker Desktop y probar la carga en Neo4j (`load_neo4j.py` no se ha podido ejecutar).
- Descargar el histórico completo (643, 1143 y 1044) y migrar la consolidación a PySpark (ADR-001).
- Revisar I6 (precios unitarios) y contrastar I3 con los criterios de la OIReScon.
- Semanas 7-9 (enero): Ollama con 20 pliegos y exploración del BORME.
