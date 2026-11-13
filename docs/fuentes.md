# Fuentes de datos

Cada fuente se verifica con peticiones reales antes de implementarla. Fecha de verificación en cada
ficha. Estado: ✅ verificada e implementada · 🟡 verificada, pendiente de implementar · ⏳ sin verificar.

## ✅ PLACSP — licitaciones (sindicación 643)

- **Verificada:** 28/10/2026.
- **Página:** https://www.hacienda.gob.es/es-ES/GobiernoAbierto/Datos%20Abiertos/Paginas/LicitacionesContratante.aspx
- **Qué contiene:** licitaciones de los perfiles de contratante alojados en PLACSP, **sin contratos
  menores**.
- **URLs:**
  - Feed vivo: `https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom`
  - Anuales 2012-2025: `.../sindicacion_643/licitacionesPerfilesContratanteCompleto3_AAAA.zip`
  - Mensuales 2025-2026 (hasta 202610 a fecha de verificación): `..._AAAAMM.zip`. También existe `..._2026.zip`.
- **Formato:** zip con ficheros Atom de un máximo de 500 entradas cada uno, enlazados con
  `link rel="next"`. Cada entrada contiene un `cac-place-ext:ContractFolderStatus` en CODICE
  (UBL adaptado). Las anulaciones se publican como `at:deleted-entry`.
- **Actualización:** diaria. Una misma licitación aparece tantas veces como modificaciones haya tenido
  (de ahí la deduplicación por `updated`, ADR-006).
- **Licencia:** condiciones generales de reutilización de la información del sector público (Ley 37/2007
  y Real Decreto 1495/2011), que permiten el uso comercial y no comercial con cita de la fuente. Ver
  https://www.hacienda.gob.es/es-ES/Paginas/Avisolegal.aspx y https://datos.gob.es/avisolegal.
- **Volumen:** ver tabla de descargas al final.
- **Campos clave extraídos** (`pipelines/transform/codice.py`): identificador y URL de la entrada, fecha
  de actualización, expediente, estado, objeto; órgano (nombre, NIF, DIR3, ID de plataforma, tipo,
  actividad, ciudad, CP, jerarquía); tipo y subtipo de contrato; presupuesto sin y con IVA y valor
  estimado; CPV; NUTS del lugar de ejecución; procedimiento, urgencia, regulación armonizada, fin de
  plazo; fechas de anuncios (licitación, adjudicación, modificación…); lotes con presupuesto, CPV, NUTS
  y criterios de adjudicación (automáticos / juicio de valor con su peso); resultados por lote (código,
  fecha, nº de ofertas y de ofertas PYME, oferta mínima y máxima, adjudicatario con NIF, importe sin y
  con IVA, contrato).
- **Documentos adjuntos:** el feed enlaza el PCAP (`LegalDocumentReference`), el PPT
  (`TechnicalDocumentReference`) y otros documentos, con hash. Base para la capa 3.
- **Problemas detectados:**
  - Si el fichero no existe, el servidor responde **HTTP 200 con una página HTML**: la ingesta comprueba
    `Content-Type` y falla si no es zip.
  - Las peticiones `HEAD` a los zip pueden quedarse colgadas; se usa `GET` en streaming.
  - Velocidad de descarga observada: ~0,15-0,2 MB/s (un mes tarda en torno a media hora).
  - Las respuestas no incluyen `Content-Length`.

## ✅ PLACSP — contratos menores (sindicación 1143)

- **Verificada:** 28/10/2026.
- **Página:** https://www.hacienda.gob.es/es-ES/GobiernoAbierto/Datos%20Abiertos/Paginas/ContratosMenores.aspx
- **URLs:** feed `.../sindicacion_1143/contratosMenoresPerfilesContratantes.atom`; anuales desde 2018 y
  mensuales `..._AAAAMM.zip` (hasta 202610).
- **Formato y licencia:** igual que la sindicación 643.
- Imprescindible para el indicador de fraccionamiento (I3).

## 🟡 PLACSP — plataformas autonómicas agregadas (sindicación 1044)

- **Verificada:** 28/10/2026 (solo existencia de los ficheros).
- **Página:** https://www.hacienda.gob.es/es-ES/GobiernoAbierto/Datos%20Abiertos/Paginas/LicitacionesAgregacion.aspx
- **URLs:** `.../sindicacion_1044/PlataformasAgregadasSinMenores_AAAA.zip` desde 2016 y mensuales.
- **Interés:** licitaciones de comunidades autónomas con plataforma propia, que no están en la 643.
  Sin ellas, el mapa infrarrepresenta esas comunidades. Ingesta ya soportada (`--dataset agregadas`);
  falta validar que el parser cubre sus particularidades.

## ✅ Listas de códigos CODICE

- **Verificada:** 28/10/2026. Descargadas en `pipelines/reference/codelists/` desde
  `https://contrataciondelestado.es/codice/cl/<versión>/<lista>.gc` (genericode).
- **Listas:** `SyndicationTenderingProcessCode-2.07` (procedimiento), `ContractCode-2.08` (tipo de
  contrato), `ContractingAuthorityCode-2.10` (tipo de órgano), `DiligenceTypeCode-1.04` (urgencia),
  `TenderResultCode-2.09` (resultado), `SyndicationContractFolderStatusCode-2.04` (estado),
  `AwardingCriteriaCode-2.0` (criterio), `TenderingNoticeTypeCode-2.11` (tipo de anuncio) y
  `CPV2008-2.04` (9.454 códigos CPV con su descripción en español).
- **Problema:** por HTTP el servidor devuelve una página de redirección; hay que usar HTTPS (en algún
  caso con el puerto 443 explícito).

## ✅ Geometrías NUTS 2021 (Eurostat/GISCO)

- **Verificada:** 28/10/2026.
- **URL:** `https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2021_4326_LEVL_{2,3}.geojson`
- **Uso:** mapa por comunidad autónoma (19 regiones NUTS 2) y provincia (59 regiones NUTS 3). Generadas
  con `pipelines/reference/build_geo.py` en `frontend/public/geo/`.
- **Licencia:** © EuroGeographics para los límites administrativos; reutilización según la política de
  copyright de GISCO/Eurostat (citar la fuente).
- **Coincidencia con PLACSP:** el feed usa la lista `NUTS-2021`, la misma versión.

## ⏳ Pendientes de verificar

| Fuente | Fase | Nota |
|---|---|---|
| BORME (BOE datos abiertos) | 0 (ene) / 3 | Sumarios XML + PDF por provincia y día |
| Pliegos PCAP/PPT | 0 (ene) / 4 | Enlaces ya presentes en el feed |
| INE / IGN (municipios) | 1 | Para el nivel municipio del mapa |
| Umbrales LCSP por fecha | 1 | Verificar en el BOE las fechas de vigencia (ver docs/indicadores.md) |

## Descargas realizadas

Registro completo con SHA-256 en `data/raw/placsp/manifest.jsonl`.

| Fecha | Conjunto | Periodo | Tamaño | Last-Modified |
|---|---|---|---|---|
| 28/10/2026 | licitaciones (643) | 202609 | 302,9 MB (2,93 GB de XML, 193 ficheros, 95.910 entradas) | 01/10/2026 04:00:30 GMT |
| 28/10/2026 | menores (1143) | 202609 | 36,9 MB (67.623 entradas) | 01/10/2026 04:01:20 GMT |
