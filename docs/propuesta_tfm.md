# Propuesta de TFM (borrador)

> Borrador para el director de TFM. Se completa en febrero de 2027 (fase 0, semanas 10-12), con las
> cifras de viabilidad obtenidas hasta entonces. Extensión objetivo: 3-5 páginas.

**Título provisional:** Análisis visual y detección de riesgos en la contratación pública española.

**Autor:** Adrián Fuertes López. Máster Universitario en Análisis y Visualización de Datos Masivos /
Visual Analytics & Big Data (UNIR).

## 1. Contexto y motivación

La Plataforma de Contratación del Sector Público (PLACSP) publica como datos abiertos las licitaciones
y adjudicaciones de todo el sector público desde 2012. Ese volumen permite calcular de forma sistemática
indicadores de riesgo descritos en la literatura (licitador único, concentración, fraccionamiento,
procedimientos poco competitivos…) y presentarlos en una herramienta de análisis visual.

## 2. Objetivos

1. Ingerir y procesar el histórico completo de PLACSP en una arquitectura reproducible de big data.
2. Modelar organismos, empresas y contratos como un grafo y enriquecerlo con el BORME.
3. Calcular indicadores de riesgo fundamentados y detectar anomalías con ML y algoritmos de grafos.
4. Evaluar la extracción de información de pliegos con LLM local frente a modelos de API y anotación manual.
5. Construir una aplicación web de análisis visual (explorador de grafo, mapa, panel de alertas, fichas).
6. Documentar el gobierno del dato: calidad, linaje, reproducibilidad y protección de datos personales.

## 3. Metodología

Arquitectura medallion (raw/silver/gold) con Parquet, PySpark y DuckDB; Neo4j con Graph Data Science;
MongoDB para documentos y resultados de LLM; FastAPI y React. Desarrollo por capas con regla de corte
(ver `CLAUDE.md`).

## 4. Planificación

| Fase | Periodo | Horas |
|---|---|---|
| 0 · Viabilidad y prototipos | nov 2026 - feb 2027 | ~60 |
| 1 · Núcleo de datos | 15 mar - 15 abr 2027 | ~70 |
| 2 · Aplicación web | 15 abr - 15 may 2027 | ~70 |
| 3 · BORME y grafo avanzado | 15 may - 5 jun 2027 | ~50 |
| 4 · LLM sobre pliegos | 5 - 25 jun 2027 | ~50 |
| 5 · Memoria y depósito | 25 jun - 21 jul 2027 | ~60 |

## 5. Viabilidad (a completar)

- Fuentes verificadas: ver `docs/fuentes.md`.
- Pipeline mínimo funcionando con un mes real de PLACSP: ver `docs/bitacora.md`.
- Pendiente: histórico completo, prototipo de grafo en Neo4j, prueba de extracción con 20 pliegos.

## 6. Riesgos principales

Cambios de formato en PLACSP, coste de parsear el BORME, calidad de la extracción con modelo local,
falta de tiempo y aspectos legales de los datos personales. Mitigaciones en la sección 13 del plan.
