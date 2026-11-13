"""Carga los CSV de ``data/gold/neo4j/`` en Neo4j por lotes (UNWIND + MERGE).

Requiere Neo4j en marcha (``docker compose up -d neo4j``). La conexión se toma de
NEO4J_URI, NEO4J_USER y NEO4J_PASSWORD (ver .env.example).

Para el histórico completo conviene ``neo4j-admin database import`` (fase 1);
esta carga por lotes es suficiente para uno o pocos años de datos.

Uso:
    uv run python -m pipelines.graph.load_neo4j
"""

from __future__ import annotations

import csv
import logging
import os
from collections.abc import Iterator
from itertools import islice
from pathlib import Path

from neo4j import GraphDatabase

from pipelines.graph.export_neo4j import NEO4J_DIR

log = logging.getLogger(__name__)

BATCH = 5_000

CONSTRAINTS = [
    "CREATE CONSTRAINT organismo_id IF NOT EXISTS FOR (n:Organismo) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT empresa_id IF NOT EXISTS FOR (n:Empresa) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT licitacion_id IF NOT EXISTS FOR (n:Licitacion) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT lote_id IF NOT EXISTS FOR (n:Lote) REQUIRE n.id IS UNIQUE",
]

# (fichero CSV, consulta Cypher que recibe $rows)
STEPS: list[tuple[str, str]] = [
    ("organismos", "UNWIND $rows AS r MERGE (n:Organismo {id: r.id}) SET n += r"),
    ("empresas", "UNWIND $rows AS r MERGE (n:Empresa {id: r.id}) SET n += r"),
    ("licitaciones", "UNWIND $rows AS r MERGE (n:Licitacion {id: r.id}) SET n += r"),
    ("lotes", "UNWIND $rows AS r MERGE (n:Lote {id: r.id}) SET n += r"),
    (
        "convoca",
        "UNWIND $rows AS r MATCH (o:Organismo {id: r.organismo}) MATCH (l:Licitacion {id: r.licitacion}) "
        "MERGE (o)-[:CONVOCA]->(l)",
    ),
    (
        "tiene_lote",
        "UNWIND $rows AS r MATCH (l:Licitacion {id: r.licitacion}) MATCH (x:Lote {id: r.lote}) "
        "MERGE (l)-[:TIENE_LOTE]->(x)",
    ),
    (
        "adjudicataria",
        "UNWIND $rows AS r MATCH (e:Empresa {id: r.empresa}) "
        "OPTIONAL MATCH (x:Lote {id: r.lote}) MATCH (l:Licitacion {id: r.licitacion}) "
        "WITH e, r, coalesce(x, l) AS destino "
        "CREATE (e)-[:ADJUDICATARIA {importe: toFloat(r.importe), fecha: date(r.fecha), "
        "n_licitadores: toInteger(r.n_licitadores)}]->(destino)",
    ),
]


def read_batches(path: Path, size: int = BATCH) -> Iterator[list[dict[str, str | None]]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = ({k: (v if v != "" else None) for k, v in row.items()} for row in csv.DictReader(fh))
        while batch := list(islice(reader, size)):
            yield batch


def load(csv_dir: Path = NEO4J_DIR) -> None:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    auth = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "tfm-password"))
    with GraphDatabase.driver(uri, auth=auth) as driver, driver.session() as session:
        for stmt in CONSTRAINTS:
            session.run(stmt)
        # Las relaciones ADJUDICATARIA se crean con CREATE: se borran antes para que la carga sea repetible.
        session.run("MATCH ()-[r:ADJUDICATARIA]->() CALL (r) { DELETE r } IN TRANSACTIONS OF 10000 ROWS")
        for name, cypher in STEPS:
            total = 0
            for rows in read_batches(csv_dir / f"{name}.csv"):
                session.run(cypher, rows=rows)
                total += len(rows)
            log.info("%-14s %d filas", name, total)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load()


if __name__ == "__main__":
    main()
