"""Exporta nodos y relaciones del grafo a CSV (modelo de la sección 5 del plan).

Nodos: Organismo, Empresa, Licitacion, Lote.
Relaciones: CONVOCA (Organismo->Licitacion), TIENE_LOTE (Licitacion->Lote),
ADJUDICATARIA (Empresa->Lote|Licitacion, con importe y fecha).

Los CSV se generan en ``data/gold/neo4j/`` y los carga ``pipelines.graph.load_neo4j``.

Uso:
    uv run python -m pipelines.graph.export_neo4j
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from pipelines.config import GOLD_DIR, SILVER_DIR

log = logging.getLogger(__name__)

NEO4J_DIR = GOLD_DIR / "neo4j"

EXPORTS = {
    "organismos": """
        SELECT buyer_id AS id, nif, name AS nombre, type_code AS tipo, nuts2, nuts3, city AS municipio
        FROM buyers""",
    "empresas": """
        SELECT company_id AS id, nif, upper(trim(name)) AS nombre_normalizado, sme AS pyme
        FROM companies""",
    "licitaciones": """
        SELECT dataset || ':' || entry_id AS id, folder_id AS expediente, title AS objeto, cpv_main AS cpv,
               procedure_code AS procedimiento, publication_date AS fecha_pub, budget_amount AS presupuesto, url
        FROM tenders""",
    "lotes": """
        SELECT dataset || ':' || entry_id || ':' || lot_id AS id, lot_id AS numero, name AS objeto,
               cpv_main AS cpv, budget_amount AS presupuesto
        FROM lots WHERE lot_id IS NOT NULL""",
    "convoca": """
        SELECT coalesce(buyer_platform_id, buyer_nif, upper(trim(buyer_name))) AS organismo,
               dataset || ':' || entry_id AS licitacion
        FROM tenders""",
    "tiene_lote": """
        SELECT dataset || ':' || entry_id AS licitacion, dataset || ':' || entry_id || ':' || lot_id AS lote
        FROM lots WHERE lot_id IS NOT NULL""",
    "adjudicataria": """
        SELECT c.company_id AS empresa,
               CASE WHEN l.lot_id IS NOT NULL THEN c.dataset || ':' || c.entry_id || ':' || c.lot_id END AS lote,
               c.dataset || ':' || c.entry_id AS licitacion,
               c.amount AS importe, c.ref_date AS fecha, c.n_offers AS n_licitadores
        FROM contracts c
        LEFT JOIN lots l ON l.dataset = c.dataset AND l.entry_id = c.entry_id AND l.lot_id = c.lot_id""",
}


def export(silver_dir: Path = SILVER_DIR, gold_dir: Path = GOLD_DIR, out_dir: Path = NEO4J_DIR) -> dict[str, int]:
    con = duckdb.connect()
    for name in ("tenders", "lots"):
        path = (silver_dir / name / "**" / "*.parquet").as_posix()
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}', hive_partitioning=true)")
    for name in ("buyers", "companies", "contracts"):
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{(gold_dir / f'{name}.parquet').as_posix()}')")

    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for name, sql in EXPORTS.items():
        target = (out_dir / f"{name}.csv").as_posix()
        con.execute(f"COPY ({sql}) TO '{target}' (HEADER, DELIMITER ',')")
        row = con.execute(f"SELECT count(*) FROM ({sql})").fetchone()
        counts[name] = int(row[0]) if row else 0
    con.close()
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("CSV de Neo4j en %s: %s", NEO4J_DIR, export())


if __name__ == "__main__":
    main()
