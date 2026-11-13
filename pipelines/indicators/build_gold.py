"""silver -> gold: contratos con indicadores de riesgo y agregados para la app.

Indicadores con datos estructurados (capa 1), definidos en docs/indicadores.md:

    I1 Único licitador en procedimiento abierto
    I2 Concentración de adjudicaciones (HHI por órgano)        -> nivel órgano
    I3 Posible fraccionamiento de contratos menores
    I4 Procedimiento poco competitivo (negociado sin publicidad, urgencia, emergencia)
    I5 Plazo de presentación anormalmente corto
    I6 Precio anómalo (adjudicación al 100 % del presupuesto o baja atípica)
    I7 Contrato con anuncios de modificación
    I8 Recurrencia órgano-empresa en varios años                -> nivel relación

Los indicadores son señales estadísticas de riesgo, **no pruebas de irregularidad**.

Uso:
    uv run python -m pipelines.indicators.build_gold
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import duckdb

from pipelines.config import GOLD_DIR, SILVER_DIR
from pipelines.indicators import params as p
from pipelines.quality.nif import is_personal_nif, pseudonymize_person
from pipelines.reference.codelists import codelist

log = logging.getLogger(__name__)


def _in(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


def _threshold_case(date_col: str, type_col: str) -> str:
    """Expresión SQL con el umbral legal de contrato menor vigente en la fecha y tipo dados."""
    parts = []
    for start, end, works, goods, _ in p.MINOR_CONTRACT_THRESHOLDS:
        cond = f"{date_col} >= DATE '{start}' AND {date_col} < DATE '{end}'"
        parts.append(f"WHEN {cond} AND {type_col} IN {_in(p.WORKS_CODES)} THEN {works}")
        parts.append(f"WHEN {cond} AND {type_col} IN {_in(p.GOODS_SERVICES_CODES)} THEN {goods}")
    return "CASE " + " ".join(parts) + " END"


def valid(col: str) -> str:
    """Devuelve la fecha solo si está en un rango plausible (ver params.MIN_VALID_DATE)."""
    return f"CASE WHEN {col} BETWEEN DATE '{p.MIN_VALID_DATE}' AND current_date THEN {col} END"


CONTRACTS_SQL = f"""
CREATE OR REPLACE TABLE contracts_base AS
SELECT
    a.dataset, a.entry_id, a.lot_id, a.result_code, a.award_date, a.n_offers, a.n_sme_offers,
    CASE WHEN pm.nif IS NULL THEN a.winner_nif END AS winner_nif,
    coalesce(pm.pname, a.winner_name) AS winner_name,
    a.winner_sme, a.n_winners, a.amount, a.amount_tax,
    t.title, t.url, t.folder_id, t.status_code,
    t.buyer_name, t.buyer_nif, t.buyer_type_code, t.buyer_city, t.buyer_postal_code, t.buyer_hierarchy,
    coalesce(t.buyer_platform_id, t.buyer_nif, upper(trim(t.buyer_name))) AS buyer_id,
    coalesce(pm.pid, a.winner_nif, 'SIN-NIF:' || upper(trim(a.winner_name))) AS company_id,
    t.contract_type_code, t.procedure_code, t.urgency_code, t.over_threshold,
    t.publication_date, t.submission_deadline, t.n_modification_notices, t.n_lots,
    coalesce(l.cpv_main, t.cpv_main) AS cpv,
    coalesce(l.nuts_code, t.nuts_code) AS nuts_code,
    CASE WHEN l.budget_amount IS NOT NULL THEN l.budget_amount
         WHEN coalesce(t.n_lots, 0) <= 1 THEN t.budget_amount END AS budget,
    coalesce(l.criteria_subj_weight, t.criteria_subj_weight) AS subj_weight,
    coalesce(l.criteria_obj_weight, t.criteria_obj_weight) AS obj_weight,
    -- Fecha de referencia: adjudicación si es plausible; si no, publicación o actualización.
    coalesce({valid("a.award_date")}, {valid("t.publication_date")}, {valid("t.first_notice_date")}, t.updated::DATE) AS ref_date
FROM awards a
JOIN tenders t USING (dataset, entry_id)
LEFT JOIN lots l ON l.dataset = a.dataset AND l.entry_id = a.entry_id AND l.lot_id = a.lot_id
LEFT JOIN _person_map pm ON pm.nif = a.winner_nif
WHERE a.result_code IN {_in(p.AWARDED_RESULT_CODES)}
  AND (a.winner_nif IS NOT NULL OR a.winner_name IS NOT NULL);

CREATE OR REPLACE TABLE contracts_pre AS
SELECT
    *,
    dataset || ':' || entry_id || ':' || coalesce(lot_id, '0') || ':' ||
        row_number() OVER (PARTITION BY dataset, entry_id, lot_id ORDER BY company_id) AS contract_id,
    procedure_code IN {_in(p.MINOR_CONTRACT)} AS is_minor,
    amount / NULLIF(budget, 0) AS price_ratio,
    date_diff('day', publication_date, submission_deadline) AS deadline_days,
    subj_weight / NULLIF(subj_weight + obj_weight, 0) AS subjective_share,
    substr(cpv, 1, {p.SPLITTING_CPV_DIGITS}) AS cpv_split_key,
    {_threshold_case("ref_date", "contract_type_code")} AS minor_threshold,
    year(ref_date)::INTEGER AS year,
    CASE WHEN length(nuts_code) >= 4 THEN substr(nuts_code, 1, 4) END AS nuts2,
    CASE WHEN length(nuts_code) >= 5 THEN substr(nuts_code, 1, 5) END AS nuts3
FROM contracts_base;

-- Percentiles de plazo por tipo de procedimiento y contrato (solo grupos con tamaño suficiente).
CREATE OR REPLACE TABLE deadline_cut AS
SELECT procedure_code AS d_procedure, contract_type_code AS d_type, coalesce(over_threshold, false) AS d_sara,
       quantile_cont(deadline_days, {p.SHORT_DEADLINE_PERCENTILE}) AS p_cut, count(*) AS n
FROM (SELECT DISTINCT dataset, entry_id, procedure_code, contract_type_code, over_threshold, deadline_days
      FROM contracts_pre WHERE NOT is_minor AND deadline_days >= 0)
GROUP BY ALL
HAVING count(*) >= {p.MIN_GROUP_SIZE};

CREATE OR REPLACE TABLE price_cut AS
SELECT quantile_cont(price_ratio, {p.LOW_PRICE_PERCENTILE}) AS p_low
FROM contracts_pre
WHERE procedure_code IN {_in(p.PRICE_COMPETITION_PROCEDURES)}
  AND price_ratio > 0 AND price_ratio <= {p.MAX_VALID_PRICE_RATIO};

CREATE OR REPLACE TABLE contracts AS
WITH w AS (
    SELECT c.*,
        sum(amount) OVER win AS split_window_amount,
        count(*) OVER win AS split_window_count
    FROM contracts_pre c
    WINDOW win AS (
        PARTITION BY buyer_id, company_id, cpv_split_key, is_minor
        ORDER BY ref_date
        RANGE BETWEEN INTERVAL {p.SPLITTING_WINDOW_DAYS} DAYS PRECEDING AND CURRENT ROW
    )
)
SELECT w.*,
    -- I1
    CASE WHEN procedure_code IN {_in(p.OPEN_PROCEDURES)} AND n_offers IS NOT NULL THEN n_offers = 1 END
        AS f_single_bidder,
    -- I3
    CASE WHEN is_minor AND minor_threshold IS NOT NULL AND amount IS NOT NULL AND cpv_split_key IS NOT NULL
         THEN amount < minor_threshold AND split_window_amount > minor_threshold AND split_window_count >= 2 END
        AS f_splitting,
    -- I4
    CASE WHEN NOT is_minor AND procedure_code IS NOT NULL
         THEN procedure_code IN {_in(p.NEGOTIATED_NO_PUBLICITY)} OR coalesce(urgency_code IN {_in(p.URGENT_CODES)}, false) END
        AS f_non_competitive,
    -- I5
    CASE WHEN NOT is_minor AND deadline_days >= 0 AND d.p_cut IS NOT NULL THEN deadline_days < d.p_cut END
        AS f_short_deadline,
    d.p_cut AS deadline_cut,
    -- I6
    CASE WHEN procedure_code IN {_in(p.PRICE_COMPETITION_PROCEDURES)}
          AND price_ratio > 0 AND price_ratio <= {p.MAX_VALID_PRICE_RATIO}
         THEN price_ratio >= {p.FULL_PRICE_RATIO} OR price_ratio < (SELECT p_low FROM price_cut) END
        AS f_price,
    -- I7
    CASE WHEN NOT is_minor THEN n_modification_notices > 0 END AS f_modified
FROM w
LEFT JOIN deadline_cut d
  ON d.d_procedure = w.procedure_code AND d.d_type = w.contract_type_code
 AND d.d_sara = coalesce(w.over_threshold, false);

ALTER TABLE contracts ADD COLUMN n_flags INTEGER;
ALTER TABLE contracts ADD COLUMN n_applicable INTEGER;
ALTER TABLE contracts ADD COLUMN risk_score DOUBLE;
UPDATE contracts SET
    n_flags = coalesce(f_single_bidder::INT, 0) + coalesce(f_splitting::INT, 0) + coalesce(f_non_competitive::INT, 0)
            + coalesce(f_short_deadline::INT, 0) + coalesce(f_price::INT, 0) + coalesce(f_modified::INT, 0),
    n_applicable = (f_single_bidder IS NOT NULL)::INT + (f_splitting IS NOT NULL)::INT
            + (f_non_competitive IS NOT NULL)::INT + (f_short_deadline IS NOT NULL)::INT
            + (f_price IS NOT NULL)::INT + (f_modified IS NOT NULL)::INT;
UPDATE contracts SET risk_score = CASE WHEN n_applicable > 0 THEN 100.0 * n_flags / n_applicable END;
"""

AGGREGATES_SQL = f"""
-- Relaciones órgano-empresa (aristas del grafo) e I8 recurrencia.
CREATE OR REPLACE TABLE pairs AS
WITH tot AS (SELECT buyer_id, sum(amount) AS buyer_amount FROM contracts GROUP BY ALL)
SELECT c.buyer_id, c.company_id,
       count(*) AS n_contracts, sum(c.amount) AS amount,
       count(DISTINCT c.year) AS n_years, min(c.ref_date) AS first_date, max(c.ref_date) AS last_date,
       sum(c.amount) / NULLIF(any_value(tot.buyer_amount), 0) AS share_of_buyer,
       sum(c.n_flags) AS n_flags,
       count(DISTINCT c.year) >= {p.RECURRENCE_MIN_YEARS} AS f_recurrence
FROM contracts c JOIN tot USING (buyer_id)
GROUP BY ALL;

CREATE OR REPLACE TABLE buyers_base AS
SELECT buyer_id,
       mode(buyer_name) AS name, mode(buyer_nif) AS nif, mode(buyer_type_code) AS type_code,
       mode(buyer_city) AS city, mode(buyer_postal_code) AS postal_code, mode(buyer_hierarchy) AS hierarchy,
       mode(nuts2) AS nuts2, mode(nuts3) AS nuts3,
       count(*) AS n_contracts, sum(amount) AS amount, count(DISTINCT company_id) AS n_companies,
       count(f_single_bidder) AS n_open, avg(f_single_bidder::INT) AS single_bidder_rate,
       count(f_splitting) AS n_minor, avg(f_splitting::INT) AS splitting_rate,
       avg(f_non_competitive::INT) AS non_competitive_rate,
       avg(f_short_deadline::INT) AS short_deadline_rate,
       avg(f_price::INT) AS price_rate,
       avg(f_modified::INT) AS modified_rate,
       avg(subjective_share) AS subjective_share_avg,
       sum(n_flags) AS n_contract_flags,
       avg(risk_score) AS contract_score_avg
FROM contracts GROUP BY buyer_id;

-- I2: HHI (0-10.000) y cuota del principal adjudicatario por órgano.
CREATE OR REPLACE TABLE buyer_hhi AS
SELECT buyer_id,
       10000 * sum(power(share_of_buyer, 2)) AS hhi,
       max(share_of_buyer) AS top_company_share,
       arg_max(company_id, share_of_buyer) AS top_company_id
FROM pairs WHERE share_of_buyer IS NOT NULL GROUP BY buyer_id;

CREATE OR REPLACE TABLE buyer_cpv AS
WITH x AS (
    SELECT buyer_id, substr(cpv, 1, 2) AS cpv_division, company_id, sum(amount) AS amount, count(*) AS n
    FROM contracts WHERE cpv IS NOT NULL GROUP BY ALL
), s AS (
    SELECT *, amount / NULLIF(sum(amount) OVER (PARTITION BY buyer_id, cpv_division), 0) AS share FROM x
)
SELECT buyer_id, cpv_division, sum(n) AS n_contracts, sum(amount) AS amount,
       10000 * sum(power(share, 2)) AS hhi
FROM s GROUP BY buyer_id, cpv_division;

-- Puntuación agregada: media de rangos percentiles de cada tasa entre órganos comparables.
CREATE OR REPLACE TABLE buyers AS
WITH b AS (
    SELECT bb.*, h.hhi, h.top_company_share, h.top_company_id,
           bb.n_contracts >= {p.MIN_CONTRACTS_BUYER} AS eligible
    FROM buyers_base bb LEFT JOIN buyer_hhi h USING (buyer_id)
), r AS (
    SELECT buyer_id,
        CASE WHEN eligible AND single_bidder_rate IS NOT NULL THEN percent_rank() OVER (PARTITION BY eligible AND single_bidder_rate IS NOT NULL ORDER BY single_bidder_rate) END AS r1,
        CASE WHEN eligible AND hhi IS NOT NULL THEN percent_rank() OVER (PARTITION BY eligible AND hhi IS NOT NULL ORDER BY hhi) END AS r2,
        CASE WHEN eligible AND splitting_rate IS NOT NULL THEN percent_rank() OVER (PARTITION BY eligible AND splitting_rate IS NOT NULL ORDER BY splitting_rate) END AS r3,
        CASE WHEN eligible AND non_competitive_rate IS NOT NULL THEN percent_rank() OVER (PARTITION BY eligible AND non_competitive_rate IS NOT NULL ORDER BY non_competitive_rate) END AS r4,
        CASE WHEN eligible AND short_deadline_rate IS NOT NULL THEN percent_rank() OVER (PARTITION BY eligible AND short_deadline_rate IS NOT NULL ORDER BY short_deadline_rate) END AS r5,
        CASE WHEN eligible AND price_rate IS NOT NULL THEN percent_rank() OVER (PARTITION BY eligible AND price_rate IS NOT NULL ORDER BY price_rate) END AS r6,
        CASE WHEN eligible AND modified_rate IS NOT NULL THEN percent_rank() OVER (PARTITION BY eligible AND modified_rate IS NOT NULL ORDER BY modified_rate) END AS r7
    FROM b
), hhi_cut AS (
    SELECT quantile_cont(hhi, 0.95) AS p95 FROM b WHERE eligible
)
SELECT b.*,
    100 * (coalesce(r1, 0) + coalesce(r2, 0) + coalesce(r3, 0) + coalesce(r4, 0) + coalesce(r5, 0) + coalesce(r6, 0) + coalesce(r7, 0))
        / NULLIF((r1 IS NOT NULL)::INT + (r2 IS NOT NULL)::INT + (r3 IS NOT NULL)::INT + (r4 IS NOT NULL)::INT
               + (r5 IS NOT NULL)::INT + (r6 IS NOT NULL)::INT + (r7 IS NOT NULL)::INT, 0) AS risk_score,
    CASE WHEN eligible THEN b.hhi >= (SELECT p95 FROM hhi_cut) END AS f_concentration
FROM b JOIN r USING (buyer_id);

CREATE OR REPLACE TABLE companies AS
SELECT company_id,
       mode(winner_nif) AS nif, mode(winner_name) AS name, bool_or(winner_sme) AS sme,
       count(*) AS n_contracts, sum(amount) AS amount, count(DISTINCT buyer_id) AS n_buyers,
       sum(n_flags) AS n_contract_flags, avg(risk_score) AS risk_score,
       avg(f_single_bidder::INT) AS single_bidder_rate,
       min(ref_date) AS first_date, max(ref_date) AS last_date
FROM contracts GROUP BY company_id;

-- Alertas: una fila por (contrato | relación | órgano, indicador).
CREATE OR REPLACE TABLE alerts AS
WITH c AS (SELECT * FROM contracts)
SELECT 'contrato' AS level, 'I1' AS indicator, 'Único licitador' AS indicator_name, contract_id, entry_id, url,
       buyer_id, buyer_name, company_id, winner_name AS company_name, amount, ref_date, risk_score,
       'Procedimiento abierto con una sola oferta recibida.' AS explanation
FROM c WHERE f_single_bidder
UNION ALL
SELECT 'contrato', 'I3', 'Posible fraccionamiento', contract_id, entry_id, url, buyer_id, buyer_name, company_id,
       winner_name, amount, ref_date, risk_score,
       printf('Contrato menor de %.2f € (umbral %.0f €); en %d días suman %.2f € en %d contratos menores del mismo órgano, empresa y grupo CPV %s.',
              amount, minor_threshold, {p.SPLITTING_WINDOW_DAYS}, split_window_amount, split_window_count, cpv_split_key)
FROM c WHERE f_splitting
UNION ALL
SELECT 'contrato', 'I4', 'Procedimiento poco competitivo', contract_id, entry_id, url, buyer_id, buyer_name,
       company_id, winner_name, amount, ref_date, risk_score,
       concat_ws('; ',
           CASE WHEN procedure_code IN {_in(p.NEGOTIATED_NO_PUBLICITY)} THEN 'Negociado sin publicidad' END,
           CASE WHEN urgency_code = '2' THEN 'Tramitación urgente' END,
           CASE WHEN urgency_code = '3' THEN 'Tramitación de emergencia' END) || '.'
FROM c WHERE f_non_competitive
UNION ALL
SELECT 'contrato', 'I5', 'Plazo de presentación corto', contract_id, entry_id, url, buyer_id, buyer_name,
       company_id, winner_name, amount, ref_date, risk_score,
       printf('Plazo de %d días, por debajo del percentil %d (%.1f días) de su tipo de procedimiento y contrato.',
              deadline_days, {int(p.SHORT_DEADLINE_PERCENTILE * 100)}, deadline_cut)
FROM c WHERE f_short_deadline
UNION ALL
SELECT 'contrato', 'I6', 'Precio anómalo', contract_id, entry_id, url, buyer_id, buyer_name, company_id,
       winner_name, amount, ref_date, risk_score,
       CASE WHEN price_ratio >= {p.FULL_PRICE_RATIO}
            THEN printf('Adjudicado por el %.1f %% del presupuesto base de licitación.', 100 * price_ratio)
            ELSE printf('Baja atípica: adjudicado por el %.1f %% del presupuesto base.', 100 * price_ratio) END
FROM c WHERE f_price
UNION ALL
SELECT 'contrato', 'I7', 'Contrato modificado', contract_id, entry_id, url, buyer_id, buyer_name, company_id,
       winner_name, amount, ref_date, risk_score,
       printf('%d anuncio(s) de modificación de contrato publicados.', n_modification_notices)
FROM c WHERE f_modified
UNION ALL
SELECT 'relacion', 'I8', 'Recurrencia', NULL, NULL, NULL, pr.buyer_id, b.name, pr.company_id, co.name, pr.amount,
       pr.last_date, NULL,
       printf('La misma empresa obtiene adjudicaciones de este órgano en %d años distintos (%d contratos).',
              pr.n_years, pr.n_contracts)
FROM pairs pr JOIN buyers b USING (buyer_id) JOIN companies co USING (company_id) WHERE pr.f_recurrence
UNION ALL
SELECT 'organismo', 'I2', 'Concentración de adjudicaciones', NULL, NULL, NULL, b.buyer_id, b.name,
       b.top_company_id, co.name, b.amount, NULL, b.risk_score,
       printf('HHI de %.0f (percentil 95 o superior entre órganos comparables); el principal adjudicatario concentra el %.1f %% del importe.',
              b.hhi, 100 * b.top_company_share)
FROM buyers b LEFT JOIN companies co ON co.company_id = b.top_company_id WHERE b.f_concentration;

CREATE OR REPLACE TABLE territories AS
SELECT 2 AS level, nuts2 AS code, count(*) AS n_contracts, sum(amount) AS amount,
       avg(f_single_bidder::INT) AS single_bidder_rate, avg(f_non_competitive::INT) AS non_competitive_rate,
       avg(f_splitting::INT) AS splitting_rate, avg(risk_score) AS risk_score, sum(n_flags) AS n_alerts,
       count(DISTINCT buyer_id) AS n_buyers
FROM contracts WHERE nuts2 LIKE 'ES%' GROUP BY nuts2
UNION ALL
SELECT 3, nuts3, count(*), sum(amount), avg(f_single_bidder::INT), avg(f_non_competitive::INT),
       avg(f_splitting::INT), avg(risk_score), sum(n_flags), count(DISTINCT buyer_id)
FROM contracts WHERE nuts3 LIKE 'ES%' GROUP BY nuts3;

CREATE OR REPLACE TABLE monthly AS
SELECT date_trunc('month', ref_date)::DATE AS month, count(*) AS n_contracts, sum(amount) AS amount,
       avg(f_single_bidder::INT) AS single_bidder_rate, sum(n_flags) AS n_alerts
FROM contracts GROUP BY ALL ORDER BY month;

CREATE OR REPLACE TABLE cpv_divisions AS
SELECT substr(cpv, 1, 2) AS cpv_division, count(*) AS n_contracts, sum(amount) AS amount,
       avg(f_single_bidder::INT) AS single_bidder_rate
FROM contracts WHERE cpv IS NOT NULL GROUP BY ALL;

CREATE OR REPLACE TABLE kpis AS
SELECT count(*) AS n_contracts, sum(amount) AS amount,
       avg(f_single_bidder::INT) AS single_bidder_rate,
       (SELECT count(*) FROM alerts) AS n_alerts,
       count(DISTINCT buyer_id) AS n_buyers, count(DISTINCT company_id) AS n_companies,
       min(ref_date) AS date_from, max(ref_date) AS date_to
FROM contracts;
"""

GOLD_TABLES = (
    "contracts", "pairs", "buyers", "buyer_cpv", "companies", "alerts", "territories", "monthly", "cpv_divisions", "kpis",
)  # fmt: skip


def build(
    silver_dir: Path = SILVER_DIR,
    gold_dir: Path = GOLD_DIR,
    *,
    anonymize_persons: bool = False,
    salt: str = "",
) -> dict[str, int]:
    con = duckdb.connect()
    for name in ("tenders", "lots", "awards"):
        path = (silver_dir / name / "**" / "*.parquet").as_posix()
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}', hive_partitioning=true)")

    con.execute("CREATE TEMP TABLE _person_map (nif VARCHAR, pid VARCHAR, pname VARCHAR)")
    if anonymize_persons:
        nifs = [
            r[0] for r in con.execute("SELECT DISTINCT winner_nif FROM awards WHERE winner_nif IS NOT NULL").fetchall()
        ]
        rows = [(n, *pseudonymize_person(n, salt=salt)) for n in nifs if is_personal_nif(n)]
        if rows:
            con.executemany("INSERT INTO _person_map VALUES (?, ?, ?)", rows)
        log.info("Seudonimizadas %d personas físicas adjudicatarias", len(rows))

    con.execute(CONTRACTS_SQL)
    con.execute(AGGREGATES_SQL)

    # Etiquetas de división CPV desde la lista oficial (código XX000000).
    cpv = codelist("cpv")
    con.execute("ALTER TABLE cpv_divisions ADD COLUMN label VARCHAR")
    con.executemany(
        "UPDATE cpv_divisions SET label = ? WHERE cpv_division = ?",
        [(cpv.get(f"{d}000000"), d) for (d,) in con.execute("SELECT cpv_division FROM cpv_divisions").fetchall()],
    )

    gold_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for name in GOLD_TABLES:
        target = gold_dir / f"{name}.parquet"
        target.unlink(missing_ok=True)
        con.execute(f"COPY {name} TO '{target.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
        row = con.execute(f"SELECT count(*) FROM {name}").fetchone()
        counts[name] = int(row[0]) if row else 0
    con.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--anonimizar-personas",
        action="store_true",
        help="Seudonimiza NIF y nombre de adjudicatarios con DNI/NIE/KLM (usa TFM_PSEUDONYM_SALT si existe)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    counts = build(anonymize_persons=args.anonimizar_personas, salt=os.environ.get("TFM_PSEUDONYM_SALT", ""))
    log.info("Gold escrito en %s: %s", GOLD_DIR, counts)


if __name__ == "__main__":
    main()
