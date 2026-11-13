"""Descarga de una muestra de pliegos PCAP/PPT (capa 3, fase 4 del plan).

Los enlaces ya están en el feed de PLACSP (``LegalDocumentReference`` para el PCAP y
``TechnicalDocumentReference`` para el PPT). Muestra prevista: ~3.000 pliegos
estratificados por tipo de organismo y CPV, descargados de forma idempotente a
``data/raw/pliegos/`` con hash, igual que ``pipelines.ingest.placsp``.
"""

from __future__ import annotations


def download_sample(n: int = 3000) -> None:
    raise NotImplementedError("Capa 3 (fase 4): pendiente según el plan de trabajo.")
