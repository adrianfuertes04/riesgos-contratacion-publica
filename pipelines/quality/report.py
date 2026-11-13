"""Inventario de calidad de la capa silver.

Calcula nulos por columna, duplicados, NIFs inválidos y rangos de fechas e
importes, y escribe un informe Markdown en ``docs/calidad/`` con cifras reales.
También devuelve los resultados para que los tests puedan comprobar invariantes.

Uso:
    uv run python -m pipelines.quality.report
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb

from pipelines.config import DOCS_DIR, SILVER_DIR
from pipelines.indicators.params import AWARDED_RESULT_CODES, MIN_VALID_DATE
from pipelines.quality.nif import is_valid_nif, nif_kind

log = logging.getLogger(__name__)

AWARDED = "(" + ", ".join(f"'{c}'" for c in AWARDED_RESULT_CODES) + ")"


@dataclass
class QualityReport:
    counts: dict[str, int] = field(default_factory=dict)
    nulls: dict[str, dict[str, float]] = field(default_factory=dict)
    duplicates: dict[str, int] = field(default_factory=dict)
    nif_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    ranges: dict[str, tuple[object, object]] = field(default_factory=dict)
    checks: list[tuple[str, bool, str]] = field(default_factory=list)


def _silver(con: duckdb.DuckDBPyConnection, silver_dir: Path) -> None:
    for name in ("tenders", "lots", "awards"):
        path = (silver_dir / name / "**" / "*.parquet").as_posix()
        con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{path}', hive_partitioning=true)")


def _null_ratios(con: duckdb.DuckDBPyConnection, table: str) -> dict[str, float]:
    cols = [r[0] for r in con.execute(f"DESCRIBE {table}").fetchall()]
    exprs = ", ".join(f'avg(CASE WHEN "{c}" IS NULL THEN 1 ELSE 0 END) AS "{c}"' for c in cols)
    row = con.execute(f"SELECT {exprs} FROM {table}").fetchone()
    return {c: float(v or 0) for c, v in zip(cols, row or [], strict=False)}


def _nif_stats(values: list[str | None]) -> dict[str, int]:
    stats = {
        "total": 0,
        "nulos": 0,
        "validos": 0,
        "invalidos": 0,
        "DNI": 0,
        "NIE": 0,
        "CIF": 0,
        "KLM": 0,
        "otro_formato": 0,
    }
    for v in values:
        stats["total"] += 1
        if not v:
            stats["nulos"] += 1
            continue
        kind = nif_kind(v)
        stats[kind or "otro_formato"] += 1
        stats["validos" if is_valid_nif(v) else "invalidos"] += 1
    return stats


def build_report(silver_dir: Path = SILVER_DIR) -> QualityReport:
    con = duckdb.connect()
    _silver(con, silver_dir)
    rep = QualityReport()

    for name in ("tenders", "lots", "awards"):
        row = con.execute(f"SELECT count(*) FROM {name}").fetchone()
        rep.counts[name] = int(row[0]) if row else 0
        rep.nulls[name] = _null_ratios(con, name)

    dup_sql = {
        "tenders (dataset, entry_id)": "SELECT count(*) - count(DISTINCT (dataset, entry_id)) FROM tenders",
        "lots (dataset, entry_id, lot_id)": "SELECT count(*) - count(DISTINCT (dataset, entry_id, lot_id)) FROM lots",
        "awards (dataset, entry_id, lot_id, winner_nif)": (
            "SELECT count(*) - count(DISTINCT (dataset, entry_id, lot_id, winner_nif)) FROM awards"
        ),
        "tenders con mismo expediente y órgano": (
            "SELECT count(*) - count(DISTINCT (buyer_nif, folder_id)) FROM tenders"
        ),
    }
    for label, sql in dup_sql.items():
        row = con.execute(sql).fetchone()
        rep.duplicates[label] = int(row[0]) if row else 0

    buyers = [r[0] for r in con.execute("SELECT DISTINCT buyer_nif FROM tenders").fetchall()]
    winners = [r[0] for r in con.execute("SELECT DISTINCT winner_nif FROM awards").fetchall()]
    rep.nif_stats["órganos (distintos)"] = _nif_stats(buyers)
    rep.nif_stats["adjudicatarios (distintos)"] = _nif_stats(winners)

    range_sql = {
        "tenders.publication_date": "SELECT min(publication_date), max(publication_date) FROM tenders",
        "tenders.updated": "SELECT min(updated), max(updated) FROM tenders",
        "tenders.budget_amount": "SELECT min(budget_amount), max(budget_amount) FROM tenders",
        "awards.award_date": "SELECT min(award_date), max(award_date) FROM awards",
        "awards.amount": "SELECT min(amount), max(amount) FROM awards",
        "awards.n_offers": "SELECT min(n_offers), max(n_offers) FROM awards",
    }
    for label, sql in range_sql.items():
        row = con.execute(sql).fetchone()
        rep.ranges[label] = (row[0], row[1]) if row else (None, None)

    def check(name: str, sql: str, detail: str) -> None:
        row = con.execute(sql).fetchone()
        bad = int(row[0]) if row else 0
        rep.checks.append((name, bad == 0, f"{bad} filas. {detail}"))

    check("Importes negativos", "SELECT count(*) FROM awards WHERE amount < 0 OR amount_tax < 0", "Deben ser 0.")
    check("Presupuestos negativos", "SELECT count(*) FROM tenders WHERE budget_amount < 0", "Deben ser 0.")
    check(
        "Importe con IVA menor que sin IVA",
        "SELECT count(*) FROM awards WHERE amount_tax < amount - 0.01",
        "Indica campos intercambiados o errores de carga en origen.",
    )
    check(
        "Adjudicado con nº de ofertas no positivo",
        f"SELECT count(*) FROM awards WHERE n_offers <= 0 AND result_code IN {AWARDED}",
        "Un resultado adjudicado debería tener al menos una oferta (los desiertos sí pueden tener 0).",
    )
    check(
        "Fecha de adjudicación futura",
        f"SELECT count(*) FROM awards WHERE award_date > DATE '{date.today().isoformat()}'",
        "Fechas posteriores a la ejecución del informe.",
    )
    check(
        "Fin de plazo anterior al anuncio de licitación",
        "SELECT count(*) FROM tenders WHERE submission_deadline < publication_date",
        "Plazo negativo: se excluye del indicador I5.",
    )
    check(
        f"Fechas anteriores a {MIN_VALID_DATE.year}",
        f"SELECT count(*) FROM awards WHERE award_date < DATE '{MIN_VALID_DATE}'",
        "Fechas de adjudicación imposibles (p. ej. año 0026); gold usa entonces la fecha del anuncio.",
    )
    con.close()
    return rep


def _fmt(v: object) -> str:
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def to_markdown(rep: QualityReport, title: str) -> str:
    lines = [f"# {title}", "", f"Generado el {date.today().isoformat()} por `pipelines/quality/report.py`.", ""]
    lines += ["## Volumen", "", "| Tabla | Filas |", "|---|---:|"]
    lines += [f"| {k} | {v:,} |" for k, v in rep.counts.items()]
    lines += ["", "## Duplicados", "", "| Clave | Filas sobrantes |", "|---|---:|"]
    lines += [f"| {k} | {v:,} |" for k, v in rep.duplicates.items()]
    lines += [
        "",
        "## NIFs",
        "",
        "| Conjunto | Total | Nulos | Válidos | Inválidos | DNI | NIE | CIF | K/L/M | Otro formato |",
    ]
    lines += ["|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k, s in rep.nif_stats.items():
        lines.append(
            f"| {k} | {s['total']:,} | {s['nulos']:,} | {s['validos']:,} | {s['invalidos']:,} | {s['DNI']:,} | "
            f"{s['NIE']:,} | {s['CIF']:,} | {s['KLM']:,} | {s['otro_formato']:,} |"
        )
    lines += ["", "## Rangos", "", "| Campo | Mínimo | Máximo |", "|---|---|---|"]
    lines += [f"| {k} | {_fmt(a)} | {_fmt(b)} |" for k, (a, b) in rep.ranges.items()]
    lines += ["", "## Comprobaciones", "", "| Regla | Resultado | Detalle |", "|---|---|---|"]
    lines += [f"| {n} | {'OK' if ok else 'REVISAR'} | {d} |" for n, ok, d in rep.checks]
    for table, ratios in rep.nulls.items():
        lines += ["", f"## Nulos en `{table}`", "", "| Columna | % nulos |", "|---|---:|"]
        lines += [f"| {c} | {r * 100:.1f} % |" for c, r in ratios.items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nombre", default="silver", help="Sufijo del fichero de informe")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rep = build_report()
    out = DOCS_DIR / "calidad" / f"calidad_{args.nombre}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_markdown(rep, f"Inventario de calidad — {args.nombre}"), encoding="utf-8")
    log.info("Informe escrito en %s", out)
    for name, ok, detail in rep.checks:
        log.info("%-40s %s  %s", name, "OK" if ok else "REVISAR", detail)


if __name__ == "__main__":
    main()
