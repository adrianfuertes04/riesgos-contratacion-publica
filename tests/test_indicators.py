"""Comprobación de cada indicador con un silver sintético cuyo resultado se conoce de antemano."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from pipelines.indicators.build_gold import build
from tests.conftest import award, tender, write_silver


def synthetic_silver(silver: Path) -> None:
    tenders = [
        tender("T1"),  # abierto, 1 oferta -> I1
        tender("T2"),  # abierto, 3 ofertas
        tender("T3", procedure_code="3"),  # negociado sin publicidad -> I4
        tender("T4"),  # adjudicado al 100 % -> I6
        tender("T5", n_modification_notices=2),  # -> I7
        tender("T6", urgency_code="3"),  # emergencia -> I4
        # Contratos menores de servicios (umbral LCSP 15.000 €), mismo grupo CPV 722.
        tender("M1", procedure_code="6", cpv_main="72210000", budget_amount=9000.0),
        tender("M2", procedure_code="6", cpv_main="72220000", budget_amount=8000.0),
        tender("M3", procedure_code="6", cpv_main="72230000", budget_amount=16000.0),
        tender("S1", submission_deadline=date(2026, 9, 3)),  # 2 días de plazo -> I5
        tender("D1"),  # fecha de adjudicación imposible en origen
    ]
    # Grupo de referencia para el percentil de plazos (20 días).
    tenders += [tender(f"R{i}") for i in range(40)]
    # Misma pareja órgano-empresa en cuatro años distintos -> I8.
    tenders += [tender(f"Y{y}") for y in (2023, 2024, 2025)]

    awards = [
        award("T1", n_offers=1),
        award("T2", n_offers=3, winner_nif="B87654321", winner_name="EMPRESA DOS SL"),
        award("T3", n_offers=1),
        award("T4", amount=100_000.0),
        award("T5"),
        award("T6"),
        award("M1", award_date=date(2026, 3, 1), amount=9000.0, n_offers=None),
        award("M2", award_date=date(2026, 6, 1), amount=8000.0, n_offers=None),
        award("M3", award_date=date(2026, 7, 1), amount=16000.0, n_offers=None),
        award("S1", winner_nif="B87654321", winner_name="EMPRESA DOS SL"),
        award("D1", award_date=date(26, 9, 25)),
    ]
    awards += [award(f"R{i}", winner_nif="B87654321", winner_name="EMPRESA DOS SL") for i in range(40)]
    awards += [award(f"Y{y}", award_date=date(y, 5, 1)) for y in (2023, 2024, 2025)]
    write_silver(silver, tenders, awards)


@pytest.fixture
def gold(tmp_path: Path) -> Path:
    silver, gold_dir = tmp_path / "silver", tmp_path / "gold"
    synthetic_silver(silver)
    build(silver, gold_dir)
    return gold_dir


def _flags(gold: Path) -> dict[str, dict]:
    con = duckdb.connect()
    rows = con.execute(f"SELECT * FROM read_parquet('{(gold / 'contracts.parquet').as_posix()}')").fetchall()
    cols = [d[0] for d in con.description]
    return {r["entry_id"]: r for r in (dict(zip(cols, row, strict=True)) for row in rows)}


def test_single_bidder(gold: Path) -> None:
    c = _flags(gold)
    assert c["T1"]["f_single_bidder"] is True
    assert c["T2"]["f_single_bidder"] is False
    assert c["T3"]["f_single_bidder"] is None  # no es procedimiento abierto
    assert c["M1"]["f_single_bidder"] is None


def test_non_competitive(gold: Path) -> None:
    c = _flags(gold)
    assert c["T3"]["f_non_competitive"] is True
    assert c["T6"]["f_non_competitive"] is True
    assert c["T2"]["f_non_competitive"] is False
    assert c["M1"]["f_non_competitive"] is None  # no aplica a contratos menores


def test_splitting(gold: Path) -> None:
    c = _flags(gold)
    assert c["M1"]["f_splitting"] is False  # primero de la serie: 9.000 €
    assert c["M2"]["f_splitting"] is True  # acumulado 17.000 € > 15.000 €
    assert c["M3"]["f_splitting"] is False  # por sí solo supera el umbral
    assert c["M2"]["minor_threshold"] == 15_000.0
    assert c["T1"]["f_splitting"] is None


def test_price_and_modifications(gold: Path) -> None:
    c = _flags(gold)
    assert c["T4"]["f_price"] is True
    assert c["T2"]["f_price"] is False
    assert c["T3"]["f_price"] is None  # negociado sin publicidad: el precio no se forma en concurrencia
    assert c["T5"]["f_modified"] is True
    assert c["T1"]["f_modified"] is False


def test_short_deadline(gold: Path) -> None:
    c = _flags(gold)
    assert c["S1"]["deadline_days"] == 2
    assert c["S1"]["f_short_deadline"] is True
    assert c["R0"]["f_short_deadline"] is False


def test_risk_score(gold: Path) -> None:
    c = _flags(gold)
    # T1: aplica I1, I4, I5, I6, I7 -> 1 señal de 5.
    assert c["T1"]["n_applicable"] == 5
    assert c["T1"]["n_flags"] == 1
    assert c["T1"]["risk_score"] == pytest.approx(20.0)


def test_aggregates(gold: Path) -> None:
    con = duckdb.connect()

    def q(sql: str) -> list[tuple]:
        return con.execute(sql.replace("{g}", gold.as_posix())).fetchall()

    pair = q("SELECT n_years, f_recurrence FROM '{g}/pairs.parquet' WHERE company_id = 'B12345674'")
    assert pair == [(4, True)]
    indicators = {r[0] for r in q("SELECT DISTINCT indicator FROM '{g}/alerts.parquet'")}
    assert {"I1", "I3", "I4", "I5", "I6", "I7", "I8"} <= indicators
    (hhi,) = q("SELECT hhi FROM '{g}/buyers.parquet'")[0]
    assert 0 < hhi <= 10_000
    (n,) = q("SELECT n_contracts FROM '{g}/kpis.parquet'")[0]
    assert n == 54


def test_implausible_award_date_falls_back(gold: Path) -> None:
    c = _flags(gold)
    assert c["D1"]["ref_date"] == date(2026, 9, 1)  # fecha del anuncio de licitación
    assert c["D1"]["year"] == 2026


def test_anonymize_persons(tmp_path: Path) -> None:
    silver, gold_dir = tmp_path / "silver", tmp_path / "gold"
    tenders = [tender("P1"), tender("E1")]
    awards = [
        award("P1", winner_nif="12345678Z", winner_name="JUAN PEREZ GARCIA"),
        award("E1", winner_nif="B12345674", winner_name="EMPRESA SL"),
    ]
    write_silver(silver, tenders, awards)
    build(silver, gold_dir, anonymize_persons=True, salt="s")

    con = duckdb.connect()
    parquet_path = (gold_dir / "companies.parquet").as_posix()
    rows = con.execute(
        f"SELECT company_id, nif, name FROM read_parquet('{parquet_path}') ORDER BY company_id"
    ).fetchall()
    by_id = {cid: (nif, name) for cid, nif, name in rows}
    assert "B12345674" in by_id
    assert by_id["B12345674"] == ("B12345674", "EMPRESA SL")
    pf_ids = [cid for cid in by_id if cid.startswith("PF-")]
    assert len(pf_ids) == 1
    assert by_id[pf_ids[0]][0] is None
    assert "JUAN PEREZ" not in by_id[pf_ids[0]][1]
