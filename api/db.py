"""Acceso a la capa gold con DuckDB (en memoria, vistas sobre Parquet)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import duckdb

from pipelines.config import GOLD_DIR
from pipelines.indicators.build_gold import GOLD_TABLES


class GoldDB:
    """Conexión DuckDB compartida; cada consulta usa su propio cursor."""

    def __init__(self, gold_dir: Path = GOLD_DIR) -> None:
        self.gold_dir = gold_dir
        self._con = duckdb.connect()
        self._lock = threading.Lock()
        missing = [t for t in GOLD_TABLES if not (gold_dir / f"{t}.parquet").exists()]
        if missing:
            raise RuntimeError(f"Faltan tablas gold en {gold_dir}: {missing}. Ejecuta el pipeline (ver README).")
        for table in GOLD_TABLES:
            path = (gold_dir / f"{table}.parquet").as_posix()
            self._con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{path}')")

    def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._con.cursor()
        try:
            rel = cur.execute(sql, params or [])
            cols = [d[0] for d in rel.description or []]
            return [dict(zip(cols, row, strict=True)) for row in rel.fetchall()]
        finally:
            cur.close()

    def one(self, sql: str, params: list[Any] | None = None) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None
