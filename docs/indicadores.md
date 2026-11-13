# Indicadores de riesgo

> Los indicadores son **señales estadísticas de riesgo, no pruebas de irregularidad**. Así se indica en
> la aplicación y debe indicarse en la memoria (sección 10 del plan: presunción de inocencia).

Implementación: `pipelines/indicators/build_gold.py`. Parámetros: `pipelines/indicators/params.py`.
Códigos según las listas oficiales CODICE descargadas en `pipelines/reference/codelists/`.

**Unidad de análisis.** Un *contrato* es un resultado adjudicado (`TenderResult` con código 1, 2, 8 o 9 de
`TenderResultCode-2.09`: adjudicado provisional, definitivo, adjudicado o formalizado). Se excluyen
desiertos, desistimientos, renuncias, "licitador mejor valorado" y encargos a medios propios (11).

**Fecha de referencia.** La de adjudicación; si falta o es imposible (anterior a 2008 o futura), la del
anuncio de licitación y, en su defecto, la del primer anuncio publicado.

**Aplicabilidad.** Cada indicador vale `verdadero`, `falso` o *no aplica* (nulo). Por ejemplo, el único
licitador no aplica a un negociado sin publicidad. Las tasas se calculan solo sobre los casos aplicables.

## Indicadores con datos estructurados (capa 1)

### I1 · Único licitador en procedimiento abierto

- **Definición:** contrato adjudicado en procedimiento abierto (código 1) o abierto simplificado (9)
  con una sola oferta recibida (`ReceivedTenderQuantity = 1`).
- **Nivel organismo:** % de contratos abiertos con oferta única.
- **Fuente:** Fazekas, Tóth y King (2016); indicador *single bidder* del Single Market Scoreboard de la
  Comisión Europea; OCDE (2016).
- **Umbral:** no aplica (indicador binario).
- **Limitaciones:** el número de ofertas falta en parte de los resultados; algunos organismos publican el
  número de ofertas del expediente y no del lote.

### I2 · Concentración de adjudicaciones

- **Definición:** índice Herfindahl-Hirschman del importe adjudicado por empresa dentro de cada órgano:
  `HHI = 10.000 · Σ sᵢ²`, con `sᵢ` la cuota de la empresa *i*. También por órgano y división CPV
  (tabla `buyer_cpv`) y cuota del principal adjudicatario.
- **Alerta:** HHI en el percentil 95 o superior entre órganos comparables (≥ 10 contratos).
- **Fuente:** definición del HHI en las *Horizontal Merger Guidelines* del U.S. DOJ y la FTC; uso como
  medida de concentración de proveedores en la literatura de contratación (Fazekas et al.).
- **Umbral:** estadístico (percentil 95). No se aplican los umbrales de defensa de la competencia, que
  se refieren a mercados y no a la cartera de un comprador.
- **Limitaciones:** con pocos contratos el HHI es alto por construcción; por eso se exige un mínimo.

### I3 · Posible fraccionamiento de contratos menores

- **Definición:** contrato menor (procedimiento 6) cuyo importe es inferior al umbral legal pero que,
  sumado a los contratos menores del mismo órgano con la misma empresa y el mismo grupo CPV (3 primeros
  dígitos) en los 365 días anteriores, supera dicho umbral.
- **Umbral legal:** valor estimado inferior a 40.000 € en obras y 15.000 € en suministros y servicios
  (art. 118.1 de la Ley 9/2017, LCSP, en vigor desde el 9/3/2018). Antes: 50.000 € y 18.000 € (art. 138.3
  del RDL 3/2011, TRLCSP). Se compara con el importe sin IVA.
- **Base legal de la prohibición:** art. 99.2 LCSP (no puede fraccionarse un contrato para disminuir su
  cuantía y eludir los requisitos de publicidad o de procedimiento).
- **Elecciones metodológicas:** grupo CPV de 3 dígitos como "objeto similar" y ventana de 365 días.
  Configurables. Pendiente contrastar con los criterios de los informes de supervisión de la OIReScon.
- **Limitaciones:** el indicador no puede distinguir necesidades realmente independientes; con un único
  mes de datos la ventana queda truncada.

### I4 · Procedimiento poco competitivo

- **Definición:** contrato no menor adjudicado por negociado sin publicidad (código 3) o con tramitación
  urgente (`UrgencyCode` 2) o de emergencia (3).
- **Fuente:** arts. 168 (negociado sin publicidad), 119 (tramitación urgente) y 120 (tramitación de
  emergencia) LCSP; indicador *no call for bids* del Single Market Scoreboard; Fazekas et al. (2016).
- **Limitaciones:** son procedimientos legales en sus supuestos; la señal es su frecuencia relativa.

### I5 · Plazo de presentación anormalmente corto

- **Definición:** días entre la publicación del anuncio de licitación (`DOC_CN`) y el fin del plazo de
  presentación. Se marca si queda por debajo del percentil 5 de los plazos del mismo procedimiento, tipo
  de contrato y sujeción a regulación armonizada (grupos de al menos 30 expedientes).
- **Fuente:** Fazekas, Tóth y King (2016) usan plazos cortos de presentación como *red flag* con cortes
  derivados de la distribución. Los plazos mínimos legales (art. 156 LCSP y siguientes) dependen de
  muchas variables; se documentarán en la fase 1 para contrastar.
- **Limitaciones:** las rectificaciones del anuncio pueden alterar la fecha de publicación; los plazos
  negativos se excluyen y se cuentan en el informe de calidad.

### I6 · Precio anómalo

- **Definición:** ratio importe adjudicado / presupuesto base de licitación (ambos sin IVA, del lote si
  existe). Se marca si el ratio es ≥ 99,9 % (adjudicación por el presupuesto íntegro) o si está por
  debajo del percentil 1 (baja atípica). Ratios > 105 % se tratan como incoherencia de datos.
- **Aplicabilidad (elección metodológica):** solo procedimientos en los que el precio se forma en
  concurrencia (abierto, restringido, negociado con publicidad, diálogo competitivo, abierto simplificado
  y licitación con negociación). Con datos de septiembre de 2026, el 76,8 % de los negociados sin
  publicidad y el 75,1 % de los derivados de acuerdo marco se adjudican al 100 %: ahí el ratio no
  informa (ver `docs/bitacora.md`).
- **Fuente:** Fazekas y Kocsis (2020) relacionan precios relativos altos con menor competencia; la
  LCSP regula las ofertas anormalmente bajas en su art. 149 (parámetros fijados en cada pliego).
- **Limitaciones:** aun en abiertos, el 27 % se adjudica al ≥ 99,9 %; probablemente incluye contratos por
  precios unitarios en los que se publica el presupuesto máximo como importe. Hay que identificarlos
  antes de usar I6 en la memoria.

### I7 · Contrato modificado

- **Definición:** el expediente tiene uno o más anuncios de modificación de contrato (`DOC_MOD`,
  "Anuncio modificación de contrato" en `TenderingNoticeTypeCode-2.11`). Se cuentan fechas distintas.
- **Fuente:** arts. 203 a 207 LCSP (modificación de contratos); OCDE (2016) sobre la fase de ejecución.
- **Limitaciones:** las prórrogas no tienen un anuncio específico en el feed; no se detectan.

### I8 · Recurrencia órgano-empresa

- **Definición:** la misma empresa obtiene adjudicaciones del mismo órgano en 3 o más años naturales
  distintos (nivel relación).
- **Elección metodológica:** 3 años, configurable.
- **Limitaciones:** necesita varios años de datos; con un solo mes no genera alertas.

## Puntuaciones agregadas

- **Contrato (0-100):** `100 · nº de indicadores activados / nº de indicadores aplicables` (I1, I3-I7).
  Es la media de *red flags* binarias, como el Corruption Risk Index (Fazekas et al., 2016) en su forma
  sin ponderar.
- **Organismo (0-100):** media de los rangos percentiles de sus tasas de I1, I3-I7 y de su HHI frente a
  órganos comparables (≥ 10 contratos). Indica la posición relativa, no una probabilidad.
- **Empresa:** media de las puntuaciones de sus contratos.

## Indicadores de fases posteriores

| Nº | Indicador | Capa | Estado |
|---|---|---|---|
| 9 | Centralidad (PageRank, betweenness) y comunidades (Louvain) | 1-2 | Fase 3, Neo4j GDS |
| 10 | Licitadores vinculados por administradores comunes | 2 | Requiere BORME |
| 11 | Empresa recién constituida con contratos relevantes | 2 | Requiere BORME |
| 12 | Administradores con número anómalo de empresas adjudicatarias | 2 | Requiere BORME |
| 13 | Peso de criterios de juicio de valor | 3 | Ya se extrae del feed (`subjective_share`) cuando PLACSP publica los criterios; el LLM lo completará desde el PCAP |
| 14 | Requisitos sospechosamente específicos | 3 | Fase 4 |
| 15 | Fraccionamiento semántico por similitud de objetos | 4 | Opcional |

## Referencias

- Fazekas, M., Tóth, I. J. y King, L. P. (2016). An Objective Corruption Risk Index Using Public
  Procurement Data. *European Journal on Criminal Policy and Research*, 22(3), 369-397.
- Fazekas, M. y Kocsis, G. (2020). Uncovering High-Level Corruption: Cross-National Objective Corruption
  Risk Indicators Using Public Procurement Data. *British Journal of Political Science*, 50(1), 155-164.
- OCDE (2016). *Preventing Corruption in Public Procurement*. OECD Publishing.
- Comisión Europea. *Single Market Scoreboard — Public procurement* (indicadores de licitador único y de
  ausencia de convocatoria).
- Ley 9/2017, de 8 de noviembre, de Contratos del Sector Público (arts. 99, 118, 119, 120, 149, 156,
  168, 203-207).
- Real Decreto Legislativo 3/2011, de 14 de noviembre, texto refundido de la Ley de Contratos del Sector
  Público (art. 138.3).
- U.S. Department of Justice y Federal Trade Commission. *Horizontal Merger Guidelines* (definición del HHI).

Pendiente (fase 1): revisar los informes de la OIReScon y de la CNMC sobre contratación en España y
verificar en el BOE las fechas exactas de vigencia de cada umbral.
