"""Pipeline completo raw -> silver -> calidad -> gold -> CSV de Neo4j sobre el feed real recortado."""

from __future__ import annotations

from pathlib import Path

import duckdb

from pipelines.graph.export_neo4j import export
from pipelines.indicators.build_gold import build
from pipelines.quality.report import build_report, to_markdown
from pipelines.transform.build_silver import consolidate, stage_zip


def test_end_to_end(sample_zip: Path, tmp_path: Path) -> None:
    silver, gold = tmp_path / "silver", tmp_path / "gold"
    staging = stage_zip(sample_zip, "licitaciones", staging_dir=silver / "_staging")
    counts = consolidate([staging], silver_dir=silver)
    assert counts == {"tenders": 3, "lots": 5, "awards": 6}

    # Idempotencia: el staging no se rehace si el zip no ha cambiado.
    marker = staging / "_SUCCESS"
    mtime = marker.stat().st_mtime
    stage_zip(sample_zip, "licitaciones", staging_dir=silver / "_staging")
    assert marker.stat().st_mtime == mtime

    report = build_report(silver)
    assert report.counts["tenders"] == 3
    assert report.duplicates["tenders (dataset, entry_id)"] == 0
    assert report.nif_stats["adjudicatarios (distintos)"]["invalidos"] == 0
    assert "Inventario" in to_markdown(report, "Inventario de prueba")

    gold_counts = build(silver, gold)
    assert gold_counts["contracts"] == 6
    assert gold_counts["kpis"] == 1

    neo = export(silver, gold, gold / "neo4j")
    assert neo["licitaciones"] == 3
    assert neo["adjudicataria"] == 6
    assert (gold / "neo4j" / "organismos.csv").exists()


def test_partitioned_by_year(sample_zip: Path, tmp_path: Path) -> None:
    silver = tmp_path / "silver"
    consolidate([stage_zip(sample_zip, "licitaciones", staging_dir=silver / "_staging")], silver_dir=silver)
    years = sorted(p.name for p in (silver / "tenders").iterdir())
    assert all(y.startswith("year=") for y in years)
    con = duckdb.connect()
    path = (silver / "tenders" / "**" / "*.parquet").as_posix()
    (n,) = con.execute(f"SELECT count(*) FROM read_parquet('{path}', hive_partitioning=true)").fetchone()  # type: ignore[misc]
    assert n == 3
