"""Esquemas explícitos de las tablas silver (Parquet)."""

from __future__ import annotations

import pyarrow as pa

TS = pa.timestamp("us", tz="UTC")

TENDERS = pa.schema(
    [
        ("dataset", pa.string()),
        ("entry_id", pa.string()),
        ("entry_uri", pa.string()),
        ("url", pa.string()),
        ("updated", TS),
        ("folder_id", pa.string()),
        ("status_code", pa.string()),
        ("title", pa.string()),
        ("buyer_name", pa.string()),
        ("buyer_nif", pa.string()),
        ("buyer_dir3", pa.string()),
        ("buyer_platform_id", pa.string()),
        ("buyer_type_code", pa.string()),
        ("buyer_activity_code", pa.string()),
        ("buyer_city", pa.string()),
        ("buyer_postal_code", pa.string()),
        ("buyer_country", pa.string()),
        ("buyer_hierarchy", pa.string()),
        ("contract_type_code", pa.string()),
        ("contract_subtype_code", pa.string()),
        ("budget_amount", pa.float64()),
        ("budget_amount_tax", pa.float64()),
        ("estimated_value", pa.float64()),
        ("cpv_main", pa.string()),
        ("cpv_codes", pa.list_(pa.string())),
        ("nuts_code", pa.string()),
        ("nuts_name", pa.string()),
        ("procedure_code", pa.string()),
        ("urgency_code", pa.string()),
        ("over_threshold", pa.bool_()),
        ("submission_deadline", pa.date32()),
        ("publication_date", pa.date32()),
        ("first_notice_date", pa.date32()),
        ("n_modification_notices", pa.int32()),
        ("n_lots", pa.int32()),
        ("criteria_subj_weight", pa.float64()),
        ("criteria_obj_weight", pa.float64()),
        ("source_file", pa.string()),
    ]
)

LOTS = pa.schema(
    [
        ("dataset", pa.string()),
        ("entry_id", pa.string()),
        ("updated", TS),
        ("lot_id", pa.string()),
        ("name", pa.string()),
        ("budget_amount", pa.float64()),
        ("budget_amount_tax", pa.float64()),
        ("cpv_main", pa.string()),
        ("nuts_code", pa.string()),
        ("criteria_subj_weight", pa.float64()),
        ("criteria_obj_weight", pa.float64()),
    ]
)

AWARDS = pa.schema(
    [
        ("dataset", pa.string()),
        ("entry_id", pa.string()),
        ("updated", TS),
        ("lot_id", pa.string()),
        ("result_code", pa.string()),
        ("award_date", pa.date32()),
        ("n_offers", pa.int32()),
        ("n_sme_offers", pa.int32()),
        ("lowest_offer", pa.float64()),
        ("highest_offer", pa.float64()),
        ("winner_nif", pa.string()),
        ("winner_name", pa.string()),
        ("n_winners", pa.int32()),
        ("winner_sme", pa.bool_()),
        ("amount", pa.float64()),
        ("amount_tax", pa.float64()),
        ("contract_id", pa.string()),
        ("contract_date", pa.date32()),
    ]
)

DELETED = pa.schema(
    [
        ("dataset", pa.string()),
        ("entry_id", pa.string()),
        ("deleted_at", TS),
        ("reason", pa.string()),
        ("source_file", pa.string()),
    ]
)

TABLES: dict[str, pa.Schema] = {"tenders": TENDERS, "lots": LOTS, "awards": AWARDS, "deleted": DELETED}
