"""Parámetros de los indicadores de riesgo.

Cada valor indica si es un **umbral legal** (con su norma) o una **elección
metodológica** del proyecto. Las elecciones metodológicas son configurables y
están justificadas en docs/indicadores.md; no son umbrales legales.
"""

from __future__ import annotations

from datetime import date

# --- Umbrales legales del contrato menor (valor estimado, IVA excluido) ---------------
# Cada tramo: (desde, hasta_exclusive, umbral obras, umbral suministros/servicios, norma)
MINOR_CONTRACT_THRESHOLDS: list[tuple[date, date, float, float, str]] = [
    (date(2011, 12, 16), date(2018, 3, 9), 50_000.0, 18_000.0, "RDL 3/2011 (TRLCSP), art. 138.3"),
    (date(2018, 3, 9), date(9999, 12, 31), 40_000.0, 15_000.0, "Ley 9/2017 (LCSP), art. 118.1"),
]

# Códigos CODICE (ContractCode-2.08) a los que aplica cada umbral.
WORKS_CODES = ("3",)
GOODS_SERVICES_CODES = ("1", "2")

# --- Códigos de procedimiento (SyndicationTenderingProcessCode-2.07) -----------------
OPEN_PROCEDURES = ("1", "9")  # Abierto, Abierto simplificado
NEGOTIATED_NO_PUBLICITY = ("3",)
MINOR_CONTRACT = ("6",)
# Urgencia (DiligenceTypeCode-1.04): 2 = Urgente, 3 = Emergencia
URGENT_CODES = ("2", "3")

# Resultados que cuentan como adjudicación (TenderResultCode-2.09):
# 1 Adj. provisional, 2 Adj. definitiva, 8 Adjudicado, 9 Formalizado.
# Se excluyen desiertos, desistimientos, renuncias, "mejor valorado" y encargos a medios propios.
AWARDED_RESULT_CODES = ("1", "2", "8", "9")

# Procedimientos en los que el precio se forma en concurrencia: abierto, restringido, negociado con
# publicidad, diálogo competitivo, abierto simplificado y licitación con negociación. En el resto
# (negociado sin publicidad, derivados de acuerdo marco, normas internas…) el ratio
# adjudicación/presupuesto no es informativo: con datos de 09/2026, el 77 % de los negociados sin
# publicidad y el 75 % de los derivados de acuerdo marco se adjudican al 100 % (docs/bitacora.md).
PRICE_COMPETITION_PROCEDURES = ("1", "2", "4", "5", "9", "13")

# --- Elecciones metodológicas (configurables) ------------------------------------------
# Fechas anteriores se consideran erróneas (la Plataforma de Contratación del Estado arranca con la
# Ley 30/2007, en vigor desde el 30/04/2008). En el feed aparecen años como 0026 o 1969.
MIN_VALID_DATE = date(2008, 1, 1)
# Fraccionamiento: nº de dígitos del CPV que definen "objeto similar" (3 = grupo CPV).
SPLITTING_CPV_DIGITS = 3
# Fraccionamiento: ventana temporal hacia atrás desde cada contrato, en días.
SPLITTING_WINDOW_DAYS = 365
# Plazo corto: percentil de la distribución de plazos del mismo tipo de procedimiento y contrato.
SHORT_DEADLINE_PERCENTILE = 0.05
# Grupos con menos observaciones no generan percentil (se marca "no aplicable").
MIN_GROUP_SIZE = 30
# Precio: adjudicación >= este porcentaje del presupuesto base se considera "al 100 %".
FULL_PRICE_RATIO = 0.999
# Ratios por encima de este valor se tratan como incoherencia de datos, no como riesgo.
MAX_VALID_PRICE_RATIO = 1.05
# Baja atípica: percentil inferior de la distribución del ratio adjudicación / presupuesto.
LOW_PRICE_PERCENTILE = 0.01
# Recurrencia: años distintos con adjudicaciones del mismo órgano a la misma empresa.
RECURRENCE_MIN_YEARS = 3
# Órganos y empresas con menos adjudicaciones no entran en rankings por riesgo o tasas.
MIN_CONTRACTS_BUYER = 10
MIN_CONTRACTS_COMPANY = 10
