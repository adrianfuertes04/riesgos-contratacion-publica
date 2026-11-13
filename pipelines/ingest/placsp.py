"""Descarga idempotente de los ficheros de datos abiertos de PLACSP.

Cada fichero se guarda tal cual (zip) en ``data/raw/placsp/<dataset>/`` y se
registra en ``data/raw/placsp/manifest.jsonl`` con su URL, tamaño, hash SHA-256
y fecha de descarga. La capa raw es inmutable: si el fichero ya existe y su hash
coincide con el del manifiesto no se vuelve a descargar.

Uso:
    uv run python -m pipelines.ingest.placsp --dataset licitaciones --periodo 202609
    uv run python -m pipelines.ingest.placsp --dataset menores --periodo 2024
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

from pipelines.config import RAW_DIR, USER_AGENT

log = logging.getLogger(__name__)

BASE_URL = "https://contrataciondelsectorpublico.gob.es/sindicacion"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = 2.0

# Conjuntos de datos publicados (verificados el 28/10/2026, ver docs/fuentes.md).
DATASETS: dict[str, tuple[str, str]] = {
    # Licitaciones de perfiles alojados en PLACSP, sin contratos menores.
    "licitaciones": ("sindicacion_643", "licitacionesPerfilesContratanteCompleto3"),
    # Contratos menores de perfiles alojados en PLACSP.
    "menores": ("sindicacion_1143", "contratosMenoresPerfilesContratantes"),
    # Licitaciones de plataformas autonómicas agregadas, sin contratos menores.
    "agregadas": ("sindicacion_1044", "PlataformasAgregadasSinMenores"),
}

PLACSP_DIR = RAW_DIR / "placsp"
MANIFEST = PLACSP_DIR / "manifest.jsonl"


@dataclass(frozen=True)
class DownloadRecord:
    dataset: str
    periodo: str
    url: str
    path: str
    bytes: int
    sha256: str
    last_modified: str | None
    downloaded_at: str


def build_url(dataset: str, periodo: str) -> str:
    """Construye la URL de un fichero anual (AAAA) o mensual (AAAAMM)."""
    if dataset not in DATASETS:
        raise ValueError(f"Dataset desconocido: {dataset}. Opciones: {sorted(DATASETS)}")
    if not (periodo.isdigit() and len(periodo) in (4, 6)):
        raise ValueError(f"Periodo inválido: {periodo!r}. Formato AAAA o AAAAMM.")
    folder, prefix = DATASETS[dataset]
    return f"{BASE_URL}/{folder}/{prefix}_{periodo}.zip"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest(manifest: Path = MANIFEST) -> dict[str, DownloadRecord]:
    """Devuelve el último registro de cada ruta del manifiesto."""
    records: dict[str, DownloadRecord] = {}
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = DownloadRecord(**json.loads(line))
                records[rec.path] = rec
    return records


def _download_with_resume(
    url: str,
    tmp: Path,
    *,
    max_attempts: int = MAX_ATTEMPTS,
    backoff: float = RETRY_BACKOFF_SECONDS,
) -> str | None:
    """Descarga ``url`` en ``tmp`` con reintentos y reanudación por rangos HTTP."""
    last_modified: str | None = None
    for attempt in range(1, max_attempts + 1):
        offset = tmp.stat().st_size if tmp.exists() else 0
        headers = {"User-Agent": USER_AGENT}
        if offset > 0:
            headers["Range"] = f"bytes={offset}-"
        try:
            with requests.get(url, stream=True, timeout=(30, 300), headers=headers) as resp:
                status = getattr(resp, "status_code", 200)
                if status == 416 and offset > 0:
                    # Rango inválido (p. ej. el fichero cambió en origen): reiniciar desde 0.
                    tmp.unlink(missing_ok=True)
                    continue
                if status in RETRY_STATUSES:
                    raise requests.HTTPError(f"HTTP {status} transitorio para {url}", response=resp)
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")
                # PLACSP responde 200 con una página HTML cuando el fichero no existe.
                if "zip" not in content_type.lower():
                    raise RuntimeError(f"Respuesta inesperada ({content_type}) para {url}")

                resuming = offset > 0 and status == 206
                mode = "ab" if resuming else "wb"
                if offset > 0 and not resuming:
                    log.info("El servidor no soporta Range (HTTP %s); se reinicia %s", status, tmp.name)
                elif resuming:
                    log.info("Reanudando %s desde %.1f MB", tmp.name, offset / 1e6)

                with tmp.open(mode) as fh:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        if chunk:
                            fh.write(chunk)
                last_modified = resp.headers.get("Last-Modified")
                return last_modified
        except requests.RequestException as exc:
            if attempt >= max_attempts:
                raise
            wait = backoff * (2 ** (attempt - 1))
            log.warning(
                "Error descargando %s (intento %d/%d): %s; reintentando en %.1fs",
                url,
                attempt,
                max_attempts,
                exc,
                wait,
            )
            time.sleep(wait)
    return last_modified


def download(dataset: str, periodo: str, *, force: bool = False, base_dir: Path = PLACSP_DIR) -> DownloadRecord:
    url = build_url(dataset, periodo)
    target = base_dir / dataset / url.rsplit("/", 1)[1]
    manifest = base_dir / "manifest.jsonl"
    rel_path = target.relative_to(base_dir).as_posix()

    known = read_manifest(manifest).get(rel_path)
    if known and target.exists() and not force:
        if sha256_of(target) == known.sha256:
            log.info("Ya descargado y verificado: %s", rel_path)
            return known
        log.warning("El hash de %s no coincide con el manifiesto; se vuelve a descargar", rel_path)

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    if force:
        tmp.unlink(missing_ok=True)
    log.info("Descargando %s", url)
    last_modified = _download_with_resume(url, tmp)
    tmp.replace(target)

    record = DownloadRecord(
        dataset=dataset,
        periodo=periodo,
        url=url,
        path=rel_path,
        bytes=target.stat().st_size,
        sha256=sha256_of(target),
        last_modified=last_modified,
        downloaded_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    with manifest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    log.info("Guardado %s (%.1f MB)", rel_path, record.bytes / 1e6)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="licitaciones")
    parser.add_argument("--periodo", nargs="+", required=True, help="Uno o varios periodos AAAA o AAAAMM")
    parser.add_argument("--force", action="store_true", help="Descargar aunque ya exista")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for periodo in args.periodo:
        download(args.dataset, periodo, force=args.force)


if __name__ == "__main__":
    main()
