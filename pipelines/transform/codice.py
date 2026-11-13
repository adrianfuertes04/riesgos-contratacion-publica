"""Parser de los feeds Atom de PLACSP con contenido CODICE.

Cada ``<entry>`` del feed contiene un ``ContractFolderStatus`` (un expediente en
un momento dado). Se aplanan en tres tablas:

- ``tenders``: una fila por entrada (expediente + versión).
- ``lots``: una fila por lote declarado en el expediente.
- ``awards``: una fila por resultado (``TenderResult``), normalmente uno por lote.

Además se recogen las entradas eliminadas (``at:deleted-entry``) en ``deleted``.

El parser es tolerante: los campos que no aparecen se dejan a ``None``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import IO, Any

from lxml import etree

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "at": "http://purl.org/atompub/tombstones/1.0",
    "cbc": "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cbc-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2",
    "cac-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2",
}

ENTRY_TAG = f"{{{NS['atom']}}}entry"
DELETED_TAG = f"{{{NS['at']}}}deleted-entry"

Row = dict[str, Any]


@dataclass
class ParsedEntry:
    tender: Row
    lots: list[Row] = field(default_factory=list)
    awards: list[Row] = field(default_factory=list)


# --------------------------------------------------------------------------- utilidades


def _text(el: etree._Element | None, path: str) -> str | None:
    if el is None:
        return None
    value = el.findtext(path, namespaces=NS)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _float(el: etree._Element | None, path: str) -> float | None:
    value = _text(el, path)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _int(el: etree._Element | None, path: str) -> int | None:
    value = _float(el, path)
    return int(value) if value is not None else None


def _bool(el: etree._Element | None, path: str) -> bool | None:
    value = _text(el, path)
    if value is None:
        return None
    return value.lower() == "true"


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        # Algunas fechas llevan zona horaria ("2024-02-08+01:00"): nos quedamos con el día.
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _party_id(party: etree._Element | None, scheme: str) -> str | None:
    if party is None:
        return None
    for pid in party.iterfind("cac:PartyIdentification/cbc:ID", NS):
        if pid.get("schemeName") == scheme and pid.text:
            return pid.text.strip()
    return None


def normalize_nif(value: str | None) -> str | None:
    """Normaliza un NIF: mayúsculas, sin espacios, guiones ni puntos, sin prefijo ES."""
    if not value:
        return None
    clean = "".join(ch for ch in value.upper() if ch.isalnum())
    if clean.startswith("ES") and len(clean) == 11:
        clean = clean[2:]
    return clean or None


def _criteria_weights(terms: etree._Element | None) -> tuple[float | None, float | None]:
    """Suma de pesos de criterios de juicio de valor (SUBJ) y automáticos (OBJ)."""
    if terms is None:
        return None, None
    subj = obj = 0.0
    found = False
    for crit in terms.iterfind("cac:AwardingTerms/cac:AwardingCriteria", NS):
        weight = _float(crit, "cbc:WeightNumeric")
        kind = _text(crit, "cbc:AwardingCriteriaTypeCode")
        if weight is None or kind not in ("SUBJ", "OBJ"):
            continue
        found = True
        if kind == "SUBJ":
            subj += weight
        else:
            obj += weight
    return (subj, obj) if found else (None, None)


def _notice_dates(cfs: etree._Element) -> dict[str, list[date]]:
    """Fechas de publicación por tipo de anuncio (DOC_CN, DOC_CAN_ADJ, DOC_MOD...)."""
    result: dict[str, list[date]] = {}
    for info in cfs.iterfind("cac-place-ext:ValidNoticeInfo", NS):
        code = _text(info, "cbc-place-ext:NoticeTypeCode")
        if not code:
            continue
        dates = [
            d
            for d in (
                _date(ref.findtext("cbc:IssueDate", namespaces=NS))
                for ref in info.iterfind(
                    "cac-place-ext:AdditionalPublicationStatus/cac-place-ext:AdditionalPublicationDocumentReference",
                    NS,
                )
            )
            if d is not None
        ]
        result.setdefault(code, []).extend(dates)
    return result


# --------------------------------------------------------------------------- entrada


def parse_entry(entry: etree._Element, *, dataset: str, source_file: str) -> ParsedEntry | None:
    cfs = entry.find("cac-place-ext:ContractFolderStatus", NS)
    if cfs is None:
        return None

    entry_uri = _text(entry, "atom:id") or ""
    entry_id = entry_uri.rstrip("/").rsplit("/", 1)[-1]
    link = entry.find("atom:link", NS)
    updated = _timestamp(_text(entry, "atom:updated"))

    party_block = cfs.find("cac-place-ext:LocatedContractingParty", NS)
    party = party_block.find("cac:Party", NS) if party_block is not None else None
    parents = [
        name.strip()
        for name in (
            p.findtext("cac:PartyName/cbc:Name", namespaces=NS)
            for p in (
                party_block.iterfind(".//cac-place-ext:ParentLocatedParty", NS) if party_block is not None else []
            )
        )
        if name
    ]

    project = cfs.find("cac:ProcurementProject", NS)
    process = cfs.find("cac:TenderingProcess", NS)
    terms = cfs.find("cac:TenderingTerms", NS)
    notices = _notice_dates(cfs)

    cpvs = [
        c.text.strip()
        for c in (
            project.iterfind("cac:RequiredCommodityClassification/cbc:ItemClassificationCode", NS)
            if project is not None
            else []
        )
        if c.text
    ]
    subj, obj = _criteria_weights(terms)

    # El plazo de presentación solo se mide desde el anuncio de licitación (DOC_CN). Los procedimientos
    # sin anuncio (p. ej. negociado sin publicidad) conservan aparte la primera fecha de cualquier anuncio.
    publication = min(notices.get("DOC_CN", []), default=None)
    first_notice = min((d for ds in notices.values() for d in ds), default=None)

    lot_elements = cfs.findall("cac:ProcurementProjectLot", NS)
    tender: Row = {
        "dataset": dataset,
        "entry_id": entry_id,
        "entry_uri": entry_uri,
        "url": link.get("href") if link is not None else None,
        "updated": updated,
        "folder_id": _text(cfs, "cbc:ContractFolderID"),
        "status_code": _text(cfs, "cbc-place-ext:ContractFolderStatusCode"),
        "title": _text(project, "cbc:Name") or _text(entry, "atom:title"),
        "buyer_name": _text(party, "cac:PartyName/cbc:Name"),
        "buyer_nif": normalize_nif(_party_id(party, "NIF")),
        "buyer_dir3": _party_id(party, "DIR3"),
        "buyer_platform_id": _party_id(party, "ID_PLATAFORMA"),
        "buyer_type_code": _text(party_block, "cbc:ContractingPartyTypeCode"),
        "buyer_activity_code": _text(party_block, "cbc:ActivityCode"),
        "buyer_city": _text(party, "cac:PostalAddress/cbc:CityName"),
        "buyer_postal_code": _text(party, "cac:PostalAddress/cbc:PostalZone"),
        "buyer_country": _text(party, "cac:PostalAddress/cac:Country/cbc:IdentificationCode"),
        "buyer_hierarchy": " > ".join(parents) or None,
        "contract_type_code": _text(project, "cbc:TypeCode"),
        "contract_subtype_code": _text(project, "cbc:SubTypeCode"),
        "budget_amount": _float(project, "cac:BudgetAmount/cbc:TaxExclusiveAmount"),
        "budget_amount_tax": _float(project, "cac:BudgetAmount/cbc:TotalAmount"),
        "estimated_value": _float(project, "cac:BudgetAmount/cbc:EstimatedOverallContractAmount"),
        "cpv_main": cpvs[0] if cpvs else None,
        "cpv_codes": cpvs,
        "nuts_code": _text(project, "cac:RealizedLocation/cbc:CountrySubentityCode"),
        "nuts_name": _text(project, "cac:RealizedLocation/cbc:CountrySubentity"),
        "procedure_code": _text(process, "cbc:ProcedureCode"),
        "urgency_code": _text(process, "cbc:UrgencyCode"),
        "over_threshold": _bool(process, "cbc:OverThresholdIndicator"),
        "submission_deadline": _date(_text(process, "cac:TenderSubmissionDeadlinePeriod/cbc:EndDate")),
        "publication_date": publication,
        "first_notice_date": first_notice,
        # Un mismo anuncio puede figurar en varios medios con la misma fecha: se cuentan fechas distintas.
        "n_modification_notices": len(set(notices.get("DOC_MOD", []))),
        "n_lots": len(lot_elements),
        "criteria_subj_weight": subj,
        "criteria_obj_weight": obj,
        "source_file": source_file,
    }

    lots: list[Row] = []
    for lot in lot_elements:
        lot_project = lot.find("cac:ProcurementProject", NS)
        lot_subj, lot_obj = _criteria_weights(lot.find("cac:TenderingTerms", NS))
        lots.append(
            {
                "dataset": dataset,
                "entry_id": entry_id,
                "updated": updated,
                "lot_id": _text(lot, "cbc:ID"),
                "name": _text(lot_project, "cbc:Name"),
                "budget_amount": _float(lot_project, "cac:BudgetAmount/cbc:TaxExclusiveAmount"),
                "budget_amount_tax": _float(lot_project, "cac:BudgetAmount/cbc:TotalAmount"),
                "cpv_main": _text(lot_project, "cac:RequiredCommodityClassification/cbc:ItemClassificationCode"),
                "nuts_code": _text(lot_project, "cac:RealizedLocation/cbc:CountrySubentityCode"),
                "criteria_subj_weight": lot_subj,
                "criteria_obj_weight": lot_obj,
            }
        )

    awards: list[Row] = []
    for res in cfs.iterfind("cac:TenderResult", NS):
        winners = res.findall("cac:WinningParty", NS)
        winner = winners[0] if winners else None
        winner_nif = _party_id(winner, "NIF")
        if winner_nif is None and winner is not None:
            # Algunos adjudicatarios se identifican con otro esquema (p. ej. extranjeros).
            winner_nif = _text(winner, "cac:PartyIdentification/cbc:ID")
        awards.append(
            {
                "dataset": dataset,
                "entry_id": entry_id,
                "updated": updated,
                "lot_id": _text(res, "cac:AwardedTenderedProject/cbc:ProcurementProjectLotID"),
                "result_code": _text(res, "cbc:ResultCode"),
                "award_date": _date(_text(res, "cbc:AwardDate")),
                "n_offers": _int(res, "cbc:ReceivedTenderQuantity"),
                "n_sme_offers": _int(res, "cbc:SMEsReceivedTenderQuantity"),
                "lowest_offer": _float(res, "cbc:LowerTenderAmount"),
                "highest_offer": _float(res, "cbc:HigherTenderAmount"),
                "winner_nif": normalize_nif(winner_nif),
                "winner_name": _text(winner, "cac:PartyName/cbc:Name"),
                "n_winners": len(winners),
                "winner_sme": _bool(res, "cbc:SMEAwardedIndicator"),
                "amount": _float(res, "cac:AwardedTenderedProject/cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount"),
                "amount_tax": _float(res, "cac:AwardedTenderedProject/cac:LegalMonetaryTotal/cbc:PayableAmount"),
                "contract_id": _text(res, "cac:Contract/cbc:ID"),
                "contract_date": _date(_text(res, "cac:Contract/cbc:IssueDate")),
            }
        )

    return ParsedEntry(tender=tender, lots=lots, awards=awards)


def parse_deleted(el: etree._Element, *, dataset: str, source_file: str) -> Row:
    ref = el.get("ref") or ""
    comment = el.find("at:comment", NS)
    return {
        "dataset": dataset,
        "entry_id": ref.rstrip("/").rsplit("/", 1)[-1],
        "deleted_at": _timestamp(el.get("when")),
        "reason": comment.get("type") if comment is not None else None,
        "source_file": source_file,
    }


def iter_feed(stream: IO[bytes], *, dataset: str, source_file: str) -> Iterator[ParsedEntry | Row]:
    """Recorre un fichero Atom en streaming y libera memoria según avanza."""
    for _, el in etree.iterparse(stream, events=("end",), tag=(ENTRY_TAG, DELETED_TAG), huge_tree=True):
        if el.tag == ENTRY_TAG:
            parsed = parse_entry(el, dataset=dataset, source_file=source_file)
            if parsed is not None:
                yield parsed
        else:
            yield parse_deleted(el, dataset=dataset, source_file=source_file)
        el.clear()
        while el.getprevious() is not None:
            parent = el.getparent()
            if parent is None:
                break
            del parent[0]
