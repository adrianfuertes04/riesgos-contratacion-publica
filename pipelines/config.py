"""Rutas y parámetros comunes del pipeline.

Todas las rutas se pueden sobrescribir con variables de entorno para que los
tests y el contenedor de la API usen directorios distintos sin tocar código.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.environ.get("TFM_DATA_DIR", ROOT_DIR / "data"))
RAW_DIR = DATA_DIR / "raw"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
SAMPLES_DIR = DATA_DIR / "samples"

DOCS_DIR = ROOT_DIR / "docs"
REFERENCE_DIR = Path(__file__).resolve().parent / "reference"

# Identificador de cliente HTTP: los organismos públicos agradecen saber quién descarga.
USER_AGENT = "prueba-proyecto-tfm/0.1 (uso academico; datos abiertos PLACSP)"
