"""API de consulta para la aplicación web (agregados, fichas, alertas, búsqueda y subgrafos).

Arranque en desarrollo:
    uv run uvicorn api.main:app --reload
"""

from __future__ import annotations

import csv
import io
import os
from functools import lru_cache
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from api.db import GoldDB
from api.models import (
    Alert,
    BuyerProfile,
    BuyerSummary,
    CompanyProfile,
    CompanySummary,
    CpvDivision,
    Graph,
    GraphEdge,
    GraphNode,
    IndicatorSummary,
    Kpis,
    MonthlyPoint,
    Page,
    SearchResult,
    Territory,
    TerritoryProfile,
)
from pipelines.indicators.params import MIN_CONTRACTS_COMPANY
from pipelines.quality.nif import is_valid_nif
from pipelines.reference.codelists import codelist

DISCLAIMER = (
    "Los indicadores son señales estadísticas de riesgo calculadas sobre datos abiertos de PLACSP. "
    "No constituyen prueba ni acusación de irregularidad alguna."
)

INDICATORS = {
    "I1": "Único licitador en procedimiento abierto",
    "I2": "Concentración de adjudicaciones (HHI)",
    "I3": "Posible fraccionamiento de contratos menores",
    "I4": "Procedimiento poco competitivo",
    "I5": "Plazo de presentación corto",
    "I6": "Precio anómalo",
    "I7": "Contrato modificado",
    "I8": "Recurrencia órgano-empresa",
}

app = FastAPI(title="TFM contratación pública — API", version="0.1.0", description=DISCLAIMER)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("TFM_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_db() -> GoldDB:
    return GoldDB()


DB = Annotated[GoldDB, Depends(get_db)]

BUYER_COLS = (
    "buyer_id, name, nif, type_code, city, nuts2, nuts3, n_contracts, amount, n_companies, "
    "single_bidder_rate, hhi, risk_score"
)
COMPANY_COLS = "company_id, nif, name, sme, n_contracts, amount, n_buyers, n_contract_flags, risk_score"
CONTRACT_COLS = (
    "contract_id, entry_id, lot_id, title, url, buyer_id, buyer_name, company_id, winner_name, procedure_code, "
    "contract_type_code, cpv, ref_date, budget, amount, n_offers, risk_score, n_flags"
)
ALERT_COLS = (
    "level, indicator, indicator_name, contract_id, entry_id, url, buyer_id, buyer_name, company_id, company_name, "
    "amount, ref_date, risk_score, explanation"
)


def _require(row: dict[str, Any] | None, what: str) -> dict[str, Any]:
    if row is None:
        raise HTTPException(status_code=404, detail=f"{what} no encontrado")
    return row


def _escape_like(text: str) -> str:
    """Escapa comodines de LIKE/ILIKE para buscar texto literal."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _csv_safe(value: Any) -> str:
    """Serializa un valor a texto CSV neutralizando fórmulas en hojas de cálculo."""
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


# --------------------------------------------------------------------------- generales


@app.get("/api/health")
def health(db: DB) -> dict[str, Any]:
    try:
        row = db.one("SELECT n_contracts FROM kpis")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Base de datos no disponible") from exc
    return {"status": "ok", "n_contracts": int(row["n_contracts"]) if row else 0}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    return {
        "disclaimer": DISCLAIMER,
        "indicators": INDICATORS,
        "procedure": codelist("procedure"),
        "contract_type": codelist("contract_type"),
        "buyer_type": codelist("buyer_type"),
    }


@app.get("/api/indicators", response_model=list[IndicatorSummary])
def indicators_summary(db: DB) -> list[dict[str, Any]]:
    rows = db.query(
        """WITH tot AS (SELECT NULLIF(n_contracts, 0) AS n_contracts FROM kpis),
           agg AS (
               SELECT indicator, any_value(level) AS level, count(*) AS n_alerts, sum(amount) AS total_amount
               FROM alerts GROUP BY indicator
           )
           SELECT a.indicator, a.level, a.n_alerts, a.total_amount,
                  CASE WHEN a.level = 'contrato' THEN a.n_alerts::DOUBLE / tot.n_contracts END AS pct_contracts
           FROM agg a CROSS JOIN tot"""
    )
    by_code = {r["indicator"]: r for r in rows}
    return [
        {
            "indicator": code,
            "name": name,
            "level": by_code[code]["level"] if code in by_code else None,
            "n_alerts": int(by_code[code]["n_alerts"]) if code in by_code else 0,
            "total_amount": by_code[code]["total_amount"] if code in by_code else 0.0,
            "pct_contracts": by_code[code]["pct_contracts"] if code in by_code else None,
        }
        for code, name in INDICATORS.items()
    ]


@app.get("/api/kpis", response_model=Kpis)
def kpis(db: DB) -> dict[str, Any]:
    return _require(db.one("SELECT * FROM kpis"), "KPIs")


@app.get("/api/monthly", response_model=list[MonthlyPoint])
def monthly(db: DB) -> list[dict[str, Any]]:
    return db.query("SELECT * FROM monthly ORDER BY month")


@app.get("/api/cpv", response_model=list[CpvDivision])
def cpv_divisions(db: DB, limit: Annotated[int, Query(ge=1, le=100)] = 10) -> list[dict[str, Any]]:
    return db.query("SELECT * FROM cpv_divisions ORDER BY amount DESC NULLS LAST LIMIT ?", [limit])


# --------------------------------------------------------------------------- organismos


@app.get("/api/buyers", response_model=list[BuyerSummary])
def buyers(
    db: DB,
    sort: Literal["amount", "risk_score", "n_contracts", "single_bidder_rate", "hhi"] = "amount",
    limit: Annotated[int, Query(ge=1, le=200)] = 10,
    nuts: str | None = None,
) -> list[dict[str, Any]]:
    where = "WHERE (? IS NULL OR nuts2 = ? OR nuts3 = ?)"
    if sort != "amount":
        where += " AND eligible"
    return db.query(
        f"SELECT {BUYER_COLS} FROM buyers {where} ORDER BY {sort} DESC NULLS LAST LIMIT ?",
        [nuts, nuts, nuts, limit],
    )


@app.get("/api/buyers/{buyer_id:path}", response_model=BuyerProfile)
def buyer_profile(buyer_id: str, db: DB) -> dict[str, Any]:
    buyer = _require(db.one("SELECT * FROM buyers WHERE buyer_id = ?", [buyer_id]), "Organismo")
    companies = db.query(
        """SELECT p.company_id AS id, c.name, p.n_contracts, p.amount, p.share_of_buyer, p.n_years, p.n_flags
           FROM pairs p JOIN companies c USING (company_id) WHERE p.buyer_id = ?
           ORDER BY p.amount DESC NULLS LAST LIMIT 15""",
        [buyer_id],
    )
    cpv = db.query(
        """SELECT b.cpv_division, d.label, b.n_contracts, b.amount, b.hhi
           FROM buyer_cpv b LEFT JOIN cpv_divisions d USING (cpv_division)
           WHERE b.buyer_id = ? ORDER BY b.amount DESC NULLS LAST LIMIT 10""",
        [buyer_id],
    )
    alerts = db.query(
        f"SELECT {ALERT_COLS} FROM alerts WHERE buyer_id = ? ORDER BY ref_date DESC NULLS LAST LIMIT 50", [buyer_id]
    )
    contracts = db.query(
        f"SELECT {CONTRACT_COLS} FROM contracts WHERE buyer_id = ? ORDER BY ref_date DESC NULLS LAST LIMIT 50",
        [buyer_id],
    )
    return {"buyer": buyer, "companies": companies, "cpv": cpv, "alerts": alerts, "contracts": contracts}


# --------------------------------------------------------------------------- empresas


@app.get("/api/companies", response_model=list[CompanySummary])
def companies(
    db: DB,
    sort: Literal["amount", "risk_score", "n_contracts", "n_buyers"] = "amount",
    limit: Annotated[int, Query(ge=1, le=200)] = 10,
) -> list[dict[str, Any]]:
    where = "WHERE n_contracts >= ?" if sort != "amount" else ""
    params: list[Any] = [MIN_CONTRACTS_COMPANY, limit] if sort != "amount" else [limit]
    return db.query(f"SELECT {COMPANY_COLS} FROM companies {where} ORDER BY {sort} DESC NULLS LAST LIMIT ?", params)


@app.get("/api/companies/{company_id:path}", response_model=CompanyProfile)
def company_profile(company_id: str, db: DB) -> dict[str, Any]:
    company = _require(db.one("SELECT * FROM companies WHERE company_id = ?", [company_id]), "Empresa")
    company["nif_valid"] = is_valid_nif(company.get("nif"))
    buyers_ = db.query(
        """SELECT p.buyer_id AS id, b.name, p.n_contracts, p.amount, p.share_of_buyer, p.n_years, p.n_flags
           FROM pairs p JOIN buyers b USING (buyer_id) WHERE p.company_id = ?
           ORDER BY p.amount DESC NULLS LAST LIMIT 15""",
        [company_id],
    )
    alerts = db.query(
        f"SELECT {ALERT_COLS} FROM alerts WHERE company_id = ? ORDER BY ref_date DESC NULLS LAST LIMIT 50",
        [company_id],
    )
    contracts = db.query(
        f"SELECT {CONTRACT_COLS} FROM contracts WHERE company_id = ? ORDER BY ref_date DESC NULLS LAST LIMIT 50",
        [company_id],
    )
    return {"company": company, "buyers": buyers_, "alerts": alerts, "contracts": contracts}


# --------------------------------------------------------------------------- alertas


def _alerts_where(
    *,
    indicator: str | None,
    level: str | None,
    buyer_id: str | None,
    company_id: str | None,
    q: str | None,
    min_amount: float | None,
    min_risk: float | None,
) -> tuple[str, list[Any]]:
    q_clean = q.strip() if q else ""
    pattern = f"%{_escape_like(q_clean)}%" if q_clean else None
    where = """WHERE (? IS NULL OR indicator = ?) AND (? IS NULL OR level = ?)
               AND (? IS NULL OR buyer_id = ?) AND (? IS NULL OR company_id = ?)
               AND (? IS NULL OR amount >= ?) AND (? IS NULL OR risk_score >= ?)
               AND (? IS NULL OR buyer_name ILIKE ? ESCAPE '\\'
                    OR company_name ILIKE ? ESCAPE '\\' OR explanation ILIKE ? ESCAPE '\\')"""
    params: list[Any] = [
        indicator,
        indicator,
        level,
        level,
        buyer_id,
        buyer_id,
        company_id,
        company_id,
        min_amount,
        min_amount,
        min_risk,
        min_risk,
        pattern,
        pattern,
        pattern,
        pattern,
    ]
    return where, params


@app.get("/api/alerts", response_model=Page[Alert])
def alerts(
    db: DB,
    indicator: str | None = None,
    level: Literal["contrato", "relacion", "organismo"] | None = None,
    buyer_id: str | None = None,
    company_id: str | None = None,
    q: str | None = None,
    min_amount: Annotated[float | None, Query(ge=0)] = None,
    min_risk: Annotated[float | None, Query(ge=0, le=100)] = None,
    sort: Literal["ref_date", "amount", "risk_score", "indicator", "buyer_name"] = "ref_date",
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    where, params = _alerts_where(
        indicator=indicator,
        level=level,
        buyer_id=buyer_id,
        company_id=company_id,
        q=q,
        min_amount=min_amount,
        min_risk=min_risk,
    )
    total = db.one(f"SELECT count(*) AS n FROM alerts {where}", params)
    items = db.query(
        f"SELECT {ALERT_COLS} FROM alerts {where} ORDER BY {sort} {order} NULLS LAST, buyer_id LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    )
    return {"items": items, "total": total["n"] if total else 0, "page": page, "size": size}


@app.get("/api/alerts/export")
def export_alerts(
    db: DB,
    indicator: str | None = None,
    level: Literal["contrato", "relacion", "organismo"] | None = None,
    buyer_id: str | None = None,
    company_id: str | None = None,
    q: str | None = None,
    min_amount: Annotated[float | None, Query(ge=0)] = None,
    min_risk: Annotated[float | None, Query(ge=0, le=100)] = None,
    sort: Literal["ref_date", "amount", "risk_score", "indicator", "buyer_name"] = "ref_date",
    order: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=10_000)] = 1000,
) -> Response:
    where, params = _alerts_where(
        indicator=indicator,
        level=level,
        buyer_id=buyer_id,
        company_id=company_id,
        q=q,
        min_amount=min_amount,
        min_risk=min_risk,
    )
    rows = db.query(
        f"SELECT {ALERT_COLS} FROM alerts {where} ORDER BY {sort} {order} NULLS LAST, buyer_id LIMIT ?",
        [*params, limit],
    )
    cols = [c.strip() for c in ALERT_COLS.split(",")]
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM UTF-8 para abrir tildes correctamente en Excel
    writer = csv.writer(buf)
    writer.writerow(cols)
    for row in rows:
        writer.writerow([_csv_safe(row.get(c)) for c in cols])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="alertas.csv"'},
    )


# --------------------------------------------------------------------------- territorio


@app.get("/api/territories", response_model=list[Territory])
def territories(db: DB, level: Annotated[int, Query(ge=2, le=3)] = 2) -> list[dict[str, Any]]:
    return db.query("SELECT * FROM territories WHERE level = ? ORDER BY code", [level])


@app.get("/api/territories/{code}", response_model=TerritoryProfile)
def territory_profile(code: str, db: DB) -> dict[str, Any]:
    territory = _require(db.one("SELECT * FROM territories WHERE code = ?", [code]), "Territorio")
    top = db.query(
        f"""SELECT {BUYER_COLS} FROM buyers WHERE nuts2 = ? OR nuts3 = ?
            ORDER BY amount DESC NULLS LAST LIMIT 10""",
        [code, code],
    )
    return {"territory": territory, "buyers": top}


# --------------------------------------------------------------------------- búsqueda y grafo


@app.get("/api/search", response_model=list[SearchResult])
def search(
    db: DB, q: Annotated[str, Query(min_length=2)], limit: Annotated[int, Query(ge=1, le=50)] = 20
) -> list[dict[str, Any]]:
    cleaned = q.strip()
    if len(cleaned) < 2:
        return []
    pattern = f"%{_escape_like(cleaned)}%"
    nif = cleaned.upper()
    return db.query(
        """SELECT * FROM (
               SELECT 'buyer' AS kind, buyer_id AS id, name, nif, n_contracts, amount FROM buyers
               WHERE name ILIKE ? ESCAPE '\\' OR nif = ?
               UNION ALL
               SELECT 'company', company_id, name, nif, n_contracts, amount FROM companies
               WHERE name ILIKE ? ESCAPE '\\' OR nif = ?
           ) ORDER BY amount DESC NULLS LAST LIMIT ?""",
        [pattern, nif, pattern, nif, limit],
    )


@app.get("/api/graph", response_model=Graph)
def graph(
    db: DB,
    node: Annotated[str, Query(description="buyer:<id> o company:<id>")],
    depth: Annotated[int, Query(ge=1, le=2)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    min_amount: Annotated[float | None, Query(ge=0)] = None,
    cpv: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    nuts: str | None = None,
    min_risk: Annotated[float | None, Query(ge=0, le=100)] = None,
) -> dict[str, Any]:
    kind, _, ref = node.partition(":")
    if kind not in ("buyer", "company") or not ref:
        raise HTTPException(status_code=422, detail="node debe ser 'buyer:<id>' o 'company:<id>'")

    filtered = """
        WITH f AS (
            SELECT buyer_id, company_id, amount, n_flags FROM contracts
            WHERE (? IS NULL OR year = ?) AND (? IS NULL OR amount >= ?) AND (? IS NULL OR substr(cpv, 1, 2) = ?)
              AND (? IS NULL OR nuts2 = ? OR nuts3 = ?) AND (? IS NULL OR risk_score >= ?)
        ), e AS (
            SELECT buyer_id, company_id, count(*) AS n_contracts, sum(amount) AS amount,
                   coalesce(sum(n_flags), 0) AS n_flags
            FROM f GROUP BY ALL
        )
    """
    fparams = [year, year, min_amount, min_amount, cpv, cpv, nuts, nuts, nuts, min_risk, min_risk]
    own, other = ("buyer_id", "company_id") if kind == "buyer" else ("company_id", "buyer_id")

    first = db.query(
        f"{filtered} SELECT * FROM e WHERE {own} = ? ORDER BY amount DESC NULLS LAST LIMIT ?",
        [*fparams, ref, limit + 1],
    )
    truncated = len(first) > limit
    edges = first[:limit]

    if depth == 2 and edges:
        neighbours = [e[other] for e in edges]
        placeholders = ", ".join("?" for _ in neighbours)
        second = db.query(
            f"""{filtered} SELECT * FROM e WHERE {other} IN ({placeholders}) AND {own} <> ?
                ORDER BY amount DESC NULLS LAST LIMIT ?""",
            [*fparams, *neighbours, ref, limit * 2 + 1],
        )
        truncated = truncated or len(second) > limit * 2
        edges += second[: limit * 2]

    buyer_ids = sorted({e["buyer_id"] for e in edges} | ({ref} if kind == "buyer" else set()))
    company_ids = sorted({e["company_id"] for e in edges} | ({ref} if kind == "company" else set()))
    nodes: list[dict[str, Any]] = []
    if buyer_ids:
        ph = ", ".join("?" for _ in buyer_ids)
        for r in db.query(
            f"SELECT buyer_id, name, amount, risk_score, n_contracts FROM buyers WHERE buyer_id IN ({ph})", buyer_ids
        ):
            nodes.append({"id": f"b:{r['buyer_id']}", "kind": "buyer", "ref": r["buyer_id"], **_node(r)})
    if company_ids:
        ph = ", ".join("?" for _ in company_ids)
        for r in db.query(
            f"SELECT company_id, name, amount, risk_score, n_contracts FROM companies WHERE company_id IN ({ph})",
            company_ids,
        ):
            nodes.append({"id": f"c:{r['company_id']}", "kind": "company", "ref": r["company_id"], **_node(r)})
    if not any(n["ref"] == ref and n["kind"] == kind for n in nodes):
        raise HTTPException(status_code=404, detail="Nodo no encontrado")

    graph_edges = [
        GraphEdge(
            source=f"b:{e['buyer_id']}",
            target=f"c:{e['company_id']}",
            n_contracts=e["n_contracts"],
            amount=e["amount"],
            n_flags=int(e["n_flags"]),
        )
        for e in edges
    ]
    return {"nodes": [GraphNode(**n) for n in nodes], "edges": graph_edges, "truncated": truncated}


def _node(row: dict[str, Any]) -> dict[str, Any]:
    return {k: row[k] for k in ("name", "amount", "risk_score", "n_contracts")}
