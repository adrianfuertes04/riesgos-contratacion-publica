"""Listas de códigos oficiales de CODICE (ficheros genericode descargados de PLACSP).

Los ``.gc`` de ``codelists/`` se descargaron el 28/10/2026 desde
https://contrataciondelestado.es/codice/cl/ (ver docs/fuentes.md).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from lxml import etree

CODELIST_DIR = Path(__file__).resolve().parent / "codelists"

FILES = {
    "procedure": "SyndicationTenderingProcessCode-2.07.gc",
    "contract_type": "ContractCode-2.08.gc",
    "buyer_type": "ContractingAuthorityCode-2.10.gc",
    "urgency": "DiligenceTypeCode-1.04.gc",
    "result": "TenderResultCode-2.09.gc",
    "status": "SyndicationContractFolderStatusCode-2.04.gc",
    "criteria": "AwardingCriteriaCode-2.0.gc",
    "notice": "TenderingNoticeTypeCode-2.11.gc",
    "cpv": "CPV2008-2.04.gc",
}


@cache
def codelist(name: str) -> dict[str, str]:
    """Devuelve ``{código: nombre en español}`` de la lista indicada."""
    tree = etree.parse(str(CODELIST_DIR / FILES[name]))
    result: dict[str, str] = {}
    for row in tree.iterfind(".//SimpleCodeList/Row"):
        values = {v.get("ColumnRef"): (v.findtext("SimpleValue") or "").strip() for v in row.iterfind("Value")}
        code = values.get("code")
        if code:
            result[code] = values.get("nombre") or values.get("name") or code
    return result


def all_codelists() -> dict[str, dict[str, str]]:
    return {name: codelist(name) for name in FILES}
