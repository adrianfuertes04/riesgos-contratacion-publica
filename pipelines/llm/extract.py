"""Extracción de pliegos con LLM local (Ollama) — capa 3, fase 4 del plan (5-25 jun 2027).

Pipeline previsto (sección 7): descargar PDF -> extraer texto (pdfplumber; OCR solo si
es escaneado) -> localizar secciones por heurísticas -> trocear -> prompt con el
esquema ``schemas.TenderDocumentExtraction`` -> validar JSON -> guardar en MongoDB
un ``ExtractionRecord`` con modelo, versión de prompt, tokens y tiempo.

Regla del plan: no se implementa hasta que la capa 1 y la app funcionen de extremo a extremo.
"""

from __future__ import annotations

from pipelines.llm.schemas import ExtractionRecord


def extract(tender_id: str, document_url: str) -> ExtractionRecord:
    raise NotImplementedError("Capa 3 (fase 4): pendiente según el plan de trabajo.")
