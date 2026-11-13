# Inventario de calidad — 202609

Generado el 2026-10-28 por `pipelines/quality/report.py`.

## Volumen

| Tabla | Filas |
|---|---:|
| tenders | 88,708 |
| lots | 29,213 |
| awards | 86,507 |

## Duplicados

| Clave | Filas sobrantes |
|---|---:|
| tenders (dataset, entry_id) | 0 |
| lots (dataset, entry_id, lot_id) | 0 |
| awards (dataset, entry_id, lot_id, winner_nif) | 84 |
| tenders con mismo expediente y órgano | 4 |

## NIFs

| Conjunto | Total | Nulos | Válidos | Inválidos | DNI | NIE | CIF | K/L/M | Otro formato |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| órganos (distintos) | 4,898 | 0 | 4,879 | 19 | 2 | 0 | 4,891 | 0 | 5 |
| adjudicatarios (distintos) | 36,545 | 1 | 31,085 | 5,459 | 4,051 | 142 | 26,935 | 0 | 5,416 |

## Rangos

| Campo | Mínimo | Máximo |
|---|---|---|
| tenders.publication_date | 2015-11-24 | 2026-09-30 |
| tenders.updated | 2021-09-29 14:31:55.605000+02:00 | 2026-10-01 02:03:10.108000+02:00 |
| tenders.budget_amount | 0.00 | 4,679,746,035.00 |
| awards.award_date | 0023-07-23 | 2026-09-30 |
| awards.amount | 0.00 | 285,720,936.00 |
| awards.n_offers | 0 | 900 |

## Comprobaciones

| Regla | Resultado | Detalle |
|---|---|---|
| Importes negativos | OK | 0 filas. Deben ser 0. |
| Presupuestos negativos | OK | 0 filas. Deben ser 0. |
| Importe con IVA menor que sin IVA | OK | 0 filas. Indica campos intercambiados o errores de carga en origen. |
| Adjudicado con nº de ofertas no positivo | OK | 0 filas. Un resultado adjudicado debería tener al menos una oferta (los desiertos sí pueden tener 0). |
| Fecha de adjudicación futura | OK | 0 filas. Fechas posteriores a la ejecución del informe. |
| Fin de plazo anterior al anuncio de licitación | REVISAR | 217 filas. Plazo negativo: se excluye del indicador I5. |
| Fechas anteriores a 2008 | REVISAR | 9 filas. Fechas de adjudicación imposibles (p. ej. año 0026); gold usa entonces la fecha del anuncio. |

## Nulos en `tenders`

| Columna | % nulos |
|---|---:|
| dataset | 0.0 % |
| entry_id | 0.0 % |
| entry_uri | 0.0 % |
| url | 0.0 % |
| updated | 0.0 % |
| folder_id | 0.0 % |
| status_code | 0.0 % |
| title | 0.0 % |
| buyer_name | 0.0 % |
| buyer_nif | 0.0 % |
| buyer_dir3 | 19.9 % |
| buyer_platform_id | 1.6 % |
| buyer_type_code | 0.0 % |
| buyer_activity_code | 1.6 % |
| buyer_city | 0.0 % |
| buyer_postal_code | 0.0 % |
| buyer_country | 0.0 % |
| buyer_hierarchy | 1.2 % |
| contract_type_code | 0.0 % |
| contract_subtype_code | 3.2 % |
| budget_amount | 0.0 % |
| budget_amount_tax | 0.0 % |
| estimated_value | 17.9 % |
| cpv_main | 25.4 % |
| cpv_codes | 0.0 % |
| nuts_code | 0.1 % |
| nuts_name | 12.7 % |
| procedure_code | 0.0 % |
| urgency_code | 1.9 % |
| over_threshold | 54.1 % |
| submission_deadline | 44.0 % |
| publication_date | 59.9 % |
| first_notice_date | 0.0 % |
| n_modification_notices | 0.0 % |
| n_lots | 0.0 % |
| criteria_subj_weight | 60.1 % |
| criteria_obj_weight | 60.1 % |
| source_file | 0.0 % |
| year | 0.0 % |

## Nulos en `lots`

| Columna | % nulos |
|---|---:|
| dataset | 0.0 % |
| entry_id | 0.0 % |
| updated | 0.0 % |
| lot_id | 0.0 % |
| name | 0.0 % |
| budget_amount | 0.0 % |
| budget_amount_tax | 0.0 % |
| cpv_main | 2.0 % |
| nuts_code | 1.4 % |
| criteria_subj_weight | 64.2 % |
| criteria_obj_weight | 64.2 % |
| year | 0.0 % |

## Nulos en `awards`

| Columna | % nulos |
|---|---:|
| dataset | 0.0 % |
| entry_id | 0.0 % |
| updated | 0.0 % |
| lot_id | 78.2 % |
| result_code | 0.0 % |
| award_date | 0.0 % |
| n_offers | 0.4 % |
| n_sme_offers | 56.5 % |
| lowest_offer | 71.6 % |
| highest_offer | 71.4 % |
| winner_nif | 4.3 % |
| winner_name | 4.3 % |
| n_winners | 0.0 % |
| winner_sme | 5.1 % |
| amount | 4.3 % |
| amount_tax | 4.3 % |
| contract_id | 65.5 % |
| contract_date | 67.3 % |
| year | 0.0 % |
