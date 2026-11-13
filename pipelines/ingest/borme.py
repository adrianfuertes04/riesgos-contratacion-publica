"""Ingesta del BORME (capa 2, fase 3 del plan: 15 may - 5 jun 2027).

Fuente: sumarios XML del BOE (datos abiertos) con enlaces a PDF por provincia y día.
Antes de implementar: verificar la API vigente, documentarla en docs/fuentes.md y
estudiar proyectos abiertos de parseo de BORME (riesgo "alto" en la sección 13).

Datos personales (sección 10): los nombres de administradores se seudonimizan
(``Persona.id_hash``) en el repositorio público y el mapeo se conserva solo en local.
"""

from __future__ import annotations


def download(day: str) -> None:
    raise NotImplementedError("Capa 2 (fase 3): pendiente según el plan de trabajo.")
