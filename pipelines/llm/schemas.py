"""Esquema JSON objetivo de la extracción de pliegos con LLM (capa 3, sección 7 del plan).

Se define ya para fijar el contrato de datos; la extracción se implementa en la fase 4.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class AwardCriterion(BaseModel):
    name: str = Field(description="Nombre del criterio tal como aparece en el pliego")
    weight: float | None = Field(default=None, ge=0, le=100, description="Ponderación en puntos o porcentaje")
    kind: Literal["formula", "juicio_valor"] = Field(description="Evaluable mediante fórmula o juicio de valor")


class SolvencyRequirement(BaseModel):
    kind: Literal["economica", "tecnica"]
    description: str
    min_amount: float | None = Field(default=None, description="Importe mínimo exigido, si lo hay")


class TenderDocumentExtraction(BaseModel):
    document_type: Literal["PCAP", "PPT", "otro"]
    award_criteria: list[AwardCriterion] = Field(default_factory=list)
    solvency: list[SolvencyRequirement] = Field(default_factory=list)
    prior_experience: str | None = Field(default=None, description="Requisitos de experiencia previa")
    submission_deadline: date | None = None
    requires_brand_or_product: bool = Field(description="Exige una marca o producto concreto")
    brand_or_product_text: str | None = None
    divided_in_lots: bool | None = None
    no_lots_reason: str | None = Field(default=None, description="Motivo de no división en lotes")
    clauses_naming_company: list[str] = Field(
        default_factory=list, description="Cláusulas que mencionan una empresa concreta (texto literal)"
    )


class ExtractionRecord(BaseModel):
    """Registro de trazabilidad que se guarda en MongoDB junto a cada extracción."""

    tender_id: str
    document_url: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    seconds: float
    result: TenderDocumentExtraction
