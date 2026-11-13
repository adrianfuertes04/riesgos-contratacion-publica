"""Descarga las geometrías NUTS 2021 de Eurostat/GISCO y genera los GeoJSON de España para la app.

- Fuente: https://gisco-services.ec.europa.eu/distribution/v2/nuts/ (escala 1:20M, EPSG:4326).
- Licencia: © EuroGeographics para los límites administrativos (ver docs/fuentes.md).
- Se conservan solo las regiones ES y se desplaza Canarias (ES70*) junto a la península,
  como es habitual en los mapas de España. El desplazamiento solo afecta a la visualización.

Uso:
    uv run python -m pipelines.reference.build_geo
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests

from pipelines.config import ROOT_DIR, USER_AGENT

log = logging.getLogger(__name__)

URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2021_4326_LEVL_{level}.geojson"
OUT_DIR = ROOT_DIR / "frontend" / "public" / "geo"
CANARIAS_SHIFT = (5.5, 7.0)  # (lon, lat) en grados


def _shift(coords: Any, dx: float, dy: float) -> Any:
    if isinstance(coords[0], (int, float)):
        return [round(coords[0] + dx, 5), round(coords[1] + dy, 5)]
    return [_shift(c, dx, dy) for c in coords]


def build(level: int, out_dir: Path = OUT_DIR) -> Path:
    resp = requests.get(URL.format(level=level), timeout=120, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    data = resp.json()
    features = []
    for feat in data["features"]:
        props = feat["properties"]
        if props.get("CNTR_CODE") != "ES":
            continue
        geom = feat["geometry"]
        if props["NUTS_ID"].startswith("ES70"):
            geom = {**geom, "coordinates": _shift(geom["coordinates"], *CANARIAS_SHIFT)}
        features.append(
            {
                "type": "Feature",
                "properties": {"code": props["NUTS_ID"], "name": props.get("NAME_LATN") or props.get("NUTS_NAME")},
                "geometry": geom,
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"nuts{level}.json"
    out.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Escrito %s (%d regiones)", out, len(features))
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for level in (2, 3):
        build(level)


if __name__ == "__main__":
    main()
