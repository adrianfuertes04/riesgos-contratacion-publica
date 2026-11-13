"""Utilidades comunes de los tests: fixture real de PLACSP y silver sintético."""

from __future__ import annotations

import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from pipelines.transform.schemas import AWARDS, LOTS, TENDERS

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_FEED = FIXTURES / "sample_feed.atom"


@pytest.fixture
def sample_zip(tmp_path: Path) -> Path:
    """Zip con la estructura de data/raw/placsp/<dataset>/ y el feed real recortado."""
    target = tmp_path / "raw" / "placsp" / "licitaciones" / "muestra.zip"
    target.parent.mkdir(parents=True)
    with zipfile.ZipFile(target, "w") as zf:
        zf.write(SAMPLE_FEED, "muestra.atom")
    return target


def _write(rows: list[dict[str, Any]], schema: pa.Schema, path: Path) -> None:
    full = [{name: row.get(name) for name in schema.names} for row in rows]
    path.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(full, schema=schema), path / "part-0.parquet")


UPDATED = datetime(2026, 9, 30, tzinfo=UTC)


def tender(entry_id: str, **kw: Any) -> dict[str, Any]:
    base = {
        "dataset": "licitaciones",
        "entry_id": entry_id,
        "updated": UPDATED,
        "title": f"Contrato {entry_id}",
        "buyer_name": "Ayuntamiento de Prueba",
        "buyer_nif": "P2800000J",
        "buyer_platform_id": "ORG1",
        "buyer_type_code": "3",
        "contract_type_code": "2",
        "procedure_code": "1",
        "urgency_code": "1",
        "cpv_main": "72000000",
        "nuts_code": "ES300",
        "budget_amount": 100_000.0,
        "publication_date": date(2026, 9, 1),
        "submission_deadline": date(2026, 9, 21),
        "n_modification_notices": 0,
        "n_lots": 0,
    }
    return base | kw


def award(entry_id: str, **kw: Any) -> dict[str, Any]:
    base = {
        "dataset": "licitaciones",
        "entry_id": entry_id,
        "updated": UPDATED,
        "result_code": "8",
        "award_date": date(2026, 9, 25),
        "n_offers": 3,
        "winner_nif": "B12345674",
        "winner_name": "EMPRESA UNO SL",
        "amount": 80_000.0,
        "amount_tax": 96_800.0,
    }
    return base | kw


def write_silver(silver: Path, tenders: list[dict], awards: list[dict], lots: list[dict] | None = None) -> None:
    for name, rows, schema in (("tenders", tenders, TENDERS), ("awards", awards, AWARDS), ("lots", lots or [], LOTS)):
        _write(rows, schema, silver / name / "year=2026")
