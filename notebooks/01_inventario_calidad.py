# %% [markdown]
# # 01 · Inventario de calidad y primeras cifras
#
# Exploración de la capa silver y gold con DuckDB. Formato *percent* (celdas `# %%`): se abre como
# notebook en VS Code o se ejecuta como script:
#
#     uv run python notebooks/01_inventario_calidad.py

# %%
import sys
from pathlib import Path

import duckdb

# Permite importar `pipelines` tanto desde la raíz del repositorio como desde notebooks/.
ROOT = Path.cwd() if (Path.cwd() / "pipelines").exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT))

from pipelines.config import GOLD_DIR, SILVER_DIR  # noqa: E402

con = duckdb.connect()
for name in ("tenders", "lots", "awards"):
    path = (SILVER_DIR / name / "**" / "*.parquet").as_posix()
    con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}', hive_partitioning=true)")
for name in ("contracts", "alerts", "buyers"):
    con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{(GOLD_DIR / f'{name}.parquet').as_posix()}')")

# %% Volumen por año de publicación y conjunto de datos
print(con.sql("SELECT dataset, year, count(*) AS expedientes FROM tenders GROUP BY ALL ORDER BY ALL"))

# %% Procedimientos
print(
    con.sql("""
        SELECT procedure_code, count(*) AS contratos, round(sum(amount) / 1e6, 1) AS millones_eur,
               round(100 * avg(f_single_bidder::INT), 1) AS pct_unico_licitador
        FROM contracts GROUP BY ALL ORDER BY contratos DESC
    """)
)

# %% Alertas por indicador
print(con.sql("SELECT indicator, indicator_name, count(*) AS n FROM alerts GROUP BY ALL ORDER BY indicator"))

# %% Distribución del número de ofertas en procedimientos abiertos
print(
    con.sql("""
        SELECT least(n_offers, 10) AS ofertas, count(*) AS contratos
        FROM contracts WHERE procedure_code IN ('1', '9') AND n_offers IS NOT NULL
        GROUP BY ALL ORDER BY ofertas
    """)
)

# %% Órganos comparables con mayor puntuación (solo exploración; no publicar como ranking)
print(
    con.sql("""
        SELECT name, n_contracts, round(risk_score, 1) AS riesgo, round(single_bidder_rate, 2) AS unico, round(hhi) AS hhi
        FROM buyers WHERE eligible ORDER BY risk_score DESC LIMIT 15
    """)
)
