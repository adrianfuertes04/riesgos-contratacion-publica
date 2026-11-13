# Prompt de extracción de pliegos — v0 (borrador, fase 4)

Eres un asistente que extrae información de pliegos de contratación pública españoles.
Devuelve **solo** un JSON válido que cumpla el esquema `TenderDocumentExtraction`
(`pipelines/llm/schemas.py`). Si un dato no aparece en el texto, usa `null` o lista vacía;
no lo deduzcas.

- `award_criteria`: cada criterio con su nombre, ponderación y si se evalúa por
  fórmula (`formula`) o por juicio de valor (`juicio_valor`).
- `solvency`: requisitos de solvencia económica y técnica, con importe mínimo si lo hay.
- `requires_brand_or_product`: `true` solo si el texto exige una marca o producto concreto
  sin admitir equivalentes.
- `clauses_naming_company`: copia literal de las cláusulas que nombran a una empresa.

Texto del pliego:

```
{texto}
```
