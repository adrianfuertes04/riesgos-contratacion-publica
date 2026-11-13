from datetime import date

from pipelines.transform.codice import ParsedEntry, iter_feed
from tests.conftest import SAMPLE_FEED


def _parse() -> tuple[list[ParsedEntry], list[dict]]:
    entries: list[ParsedEntry] = []
    deleted: list[dict] = []
    with SAMPLE_FEED.open("rb") as fh:
        for item in iter_feed(fh, dataset="licitaciones", source_file="muestra"):
            if isinstance(item, ParsedEntry):
                entries.append(item)
            else:
                deleted.append(item)
    return entries, deleted


def test_counts() -> None:
    entries, deleted = _parse()
    assert len(entries) == 3
    assert len(deleted) == 1
    assert deleted[0]["entry_id"] == "20787821"
    assert deleted[0]["reason"] == "ANULADA"


def test_multi_lot_entry() -> None:
    entries, _ = _parse()
    e = next(x for x in entries if x.tender["entry_id"] == "13703499")
    t = e.tender
    assert t["folder_id"] == "SER-23-0563-SOM"
    assert t["buyer_nif"] == "G96236443"
    assert t["contract_type_code"] == "2"
    assert t["procedure_code"] == "1"
    assert t["budget_amount"] == 55770.0
    assert t["estimated_value"] == 178464.0
    assert t["cpv_main"] == "50700000"
    assert t["publication_date"] == date(2023, 11, 13)
    assert t["first_notice_date"] == date(2023, 11, 13)
    assert t["submission_deadline"] == date(2023, 11, 29)
    assert t["n_modification_notices"] == 1
    assert t["n_lots"] == 5
    assert "Sector Público" in t["buyer_hierarchy"]

    assert len(e.lots) == 5
    lot1 = next(lot for lot in e.lots if lot["lot_id"] == "1")
    assert lot1["budget_amount"] == 13200.0
    assert lot1["nuts_code"] == "ES514"
    assert lot1["criteria_obj_weight"] == 100.0
    assert lot1["criteria_subj_weight"] == 0.0

    assert len(e.awards) == 5
    a1 = next(a for a in e.awards if a["lot_id"] == "1")
    assert a1["winner_nif"] == "B67138503"
    assert a1["winner_name"] == "QTM FACILITY, S.L."
    assert a1["n_offers"] == 4
    assert a1["amount"] == 12900.0
    assert a1["award_date"] == date(2024, 2, 8)


def test_entry_without_award() -> None:
    entries, _ = _parse()
    e = next(x for x in entries if x.tender["entry_id"] == "20435226")
    assert e.awards == []
    assert e.tender["status_code"] == "EV"
