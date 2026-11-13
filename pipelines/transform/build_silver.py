"""raw (zip con feeds Atom) -> silver (Parquet limpio, particionado por año).

Dos pasos:

1. *Staging*: cada zip de ``data/raw/placsp`` se parsea a Parquet en
   ``data/silver/_staging/<dataset>/<zip>/<tabla>.parquet``. Si el staging ya
   existe y es más reciente que el zip, se reutiliza (idempotente).
2. *Consolidación* con DuckDB: el mismo expediente aparece varias veces (una por
   actualización), así que se conserva solo la versión más reciente de cada
   ``(dataset, entry_id)``, se descartan las entradas eliminadas después de esa
   versión y se escribe ``data/silver/<tabla>/year=AAAA/*.parquet``.

Uso:
    uv run python -m pipelines.transform.build_silver
"""

from __future__ import annotations

import argparse
import logging
import shutil
import zipfile
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from pipelines.config import RAW_DIR, SILVER_DIR
from pipelines.transform.codice import ParsedEntry, iter_feed
from pipelines.transform.schemas import TABLES

log = logging.getLogger(__name__)

STAGING_DIR = SILVER_DIR / "_staging"
BATCH_ROWS = 20_000


class _TableWriter:
    """Acumula filas y las escribe por lotes en un único Parquet."""

    def __init__(self, path: Path, schema: pa.Schema) -> None:
        self.path = path
        self.schema = schema
        self.rows: list[dict] = []
        self.writer: pq.ParquetWriter | None = None
        self.count = 0

    def add(self, row: dict) -> None:
        self.rows.append(row)
        if len(self.rows) >= BATCH_ROWS:
            self.flush()

    def flush(self) -> None:
        if not self.rows:
            return
        table = pa.Table.from_pylist(self.rows, schema=self.schema)
        if self.writer is None:
            self.writer = pq.ParquetWriter(self.path, self.schema, compression="zstd")
        self.writer.write_table(table)
        self.count += len(self.rows)
        self.rows.clear()

    def close(self) -> None:
        self.flush()
        if self.writer is None:
            # Tabla vacía: se escribe igualmente para que el esquema exista.
            pq.write_table(self.schema.empty_table(), self.path, compression="zstd")
        else:
            self.writer.close()


def stage_zip(zip_path: Path, dataset: str, *, staging_dir: Path = STAGING_DIR, force: bool = False) -> Path:
    out_dir = staging_dir / dataset / zip_path.stem
    marker = out_dir / "_SUCCESS"
    if marker.exists() and marker.stat().st_mtime >= zip_path.stat().st_mtime and not force:
        log.info("Staging al día: %s", out_dir)
        return out_dir

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    writers = {name: _TableWriter(out_dir / f"{name}.parquet", schema) for name, schema in TABLES.items()}

    with zipfile.ZipFile(zip_path) as zf:
        members = sorted(n for n in zf.namelist() if n.endswith(".atom"))
        log.info("Parseando %s (%d ficheros atom)", zip_path.name, len(members))
        for member in members:
            source = f"{zip_path.name}!{member}"
            with zf.open(member) as fh:
                for item in iter_feed(fh, dataset=dataset, source_file=source):
                    if isinstance(item, ParsedEntry):
                        writers["tenders"].add(item.tender)
                        for lot in item.lots:
                            writers["lots"].add(lot)
                        for award in item.awards:
                            writers["awards"].add(award)
                    else:
                        writers["deleted"].add(item)

    for w in writers.values():
        w.close()
    marker.touch()
    log.info("Staging %s: %s", zip_path.name, {k: w.count for k, w in writers.items()})
    return out_dir


CONSOLIDATE_SQL = """
CREATE OR REPLACE TEMP VIEW staged_tenders AS SELECT * FROM read_parquet({tenders}, union_by_name=true);
CREATE OR REPLACE TEMP VIEW staged_lots    AS SELECT * FROM read_parquet({lots}, union_by_name=true);
CREATE OR REPLACE TEMP VIEW staged_awards  AS SELECT * FROM read_parquet({awards}, union_by_name=true);
CREATE OR REPLACE TEMP VIEW staged_deleted AS SELECT * FROM read_parquet({deleted}, union_by_name=true);

-- Última versión de cada expediente; empate en "updated" -> fichero más reciente.
CREATE OR REPLACE TEMP TABLE latest AS
SELECT * FROM staged_tenders
QUALIFY row_number() OVER (PARTITION BY dataset, entry_id ORDER BY updated DESC, source_file DESC) = 1;

-- Se eliminan las entradas anuladas/borradas después de su última versión.
CREATE OR REPLACE TEMP TABLE tenders AS
SELECT l.*, year(coalesce(l.publication_date, l.first_notice_date, l.updated::DATE))::INTEGER AS year
FROM latest l
WHERE NOT EXISTS (
    SELECT 1 FROM staged_deleted d
    WHERE d.dataset = l.dataset AND d.entry_id = l.entry_id AND d.deleted_at >= l.updated
);

CREATE OR REPLACE TEMP TABLE lots AS
SELECT DISTINCT ON (s.dataset, s.entry_id, s.lot_id) s.*, t.year
FROM staged_lots s JOIN tenders t USING (dataset, entry_id, updated);

-- DISTINCT: la misma versión puede venir repetida en dos ficheros del feed.
CREATE OR REPLACE TEMP TABLE awards AS
SELECT DISTINCT s.*, t.year
FROM staged_awards s JOIN tenders t USING (dataset, entry_id, updated);
"""


def consolidate(staging_dirs: list[Path], silver_dir: Path = SILVER_DIR) -> dict[str, int]:
    def files(name: str) -> str:
        return "[" + ", ".join(f"'{(d / f'{name}.parquet').as_posix()}'" for d in staging_dirs) + "]"

    con = duckdb.connect()
    con.execute(CONSOLIDATE_SQL.format(**{name: files(name) for name in TABLES}))
    counts: dict[str, int] = {}
    for name in ("tenders", "lots", "awards"):
        target = silver_dir / name
        if target.exists():
            shutil.rmtree(target)
        con.execute(f"COPY {name} TO '{target.as_posix()}' (FORMAT parquet, PARTITION_BY (year), COMPRESSION zstd)")
        row = con.execute(f"SELECT count(*) FROM {name}").fetchone()
        counts[name] = int(row[0]) if row else 0
    con.close()
    return counts


def find_raw_zips(base: Path = RAW_DIR / "placsp") -> list[tuple[str, Path]]:
    return [(p.parent.name, p) for p in sorted(base.glob("*/*.zip"))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="Reparsear aunque el staging esté al día")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    zips = find_raw_zips()
    if not zips:
        raise SystemExit("No hay ficheros en data/raw/placsp. Ejecuta antes pipelines.ingest.placsp")
    staging = [stage_zip(path, dataset, force=args.force) for dataset, path in zips]
    counts = consolidate(staging)
    log.info("Silver escrito en %s: %s", SILVER_DIR, counts)


if __name__ == "__main__":
    main()
