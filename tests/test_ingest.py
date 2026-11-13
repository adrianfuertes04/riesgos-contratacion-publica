from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import requests

from pipelines.ingest import placsp


def test_build_url() -> None:
    assert placsp.build_url("licitaciones", "202609") == (
        "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/"
        "licitacionesPerfilesContratanteCompleto3_202609.zip"
    )
    assert placsp.build_url("menores", "2024").endswith(
        "sindicacion_1143/contratosMenoresPerfilesContratantes_2024.zip"
    )
    with pytest.raises(ValueError):
        placsp.build_url("licitaciones", "2026-09")
    with pytest.raises(ValueError):
        placsp.build_url("otro", "2026")


class _FakeResponse:
    def __init__(self, body: bytes, content_type: str = "application/zip", status_code: int = 200) -> None:
        self.body = body
        self.status_code = status_code
        self.headers = {"Content-Type": content_type, "Last-Modified": "Thu, 01 Oct 2026 04:00:30 GMT"}

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return [self.body]


def test_download_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get(url: str, **kwargs: Any) -> _FakeResponse:
        calls.append(url)
        return _FakeResponse(b"PK fake zip")

    monkeypatch.setattr(placsp.requests, "get", fake_get)
    first = placsp.download("licitaciones", "202609", base_dir=tmp_path)
    second = placsp.download("licitaciones", "202609", base_dir=tmp_path)
    assert len(calls) == 1
    assert first == second
    assert first.bytes == len(b"PK fake zip")
    assert (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").count("\n") == 1

    # Si el fichero se corrompe, se vuelve a descargar.
    (tmp_path / first.path).write_bytes(b"corrupto")
    placsp.download("licitaciones", "202609", base_dir=tmp_path)
    assert len(calls) == 2


def test_download_rejects_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(placsp.requests, "get", lambda url, **kw: _FakeResponse(b"<html>", "text/html"))
    with pytest.raises(RuntimeError):
        placsp.download("menores", "209901", base_dir=tmp_path)


def test_download_resumes_and_retries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    part = tmp_path / "licitaciones" / "licitacionesPerfilesContratanteCompleto3_202609.part"
    part.parent.mkdir(parents=True)
    part.write_bytes(b"PK ")
    seen_ranges: list[str | None] = []
    attempts = 0

    def fake_get(url: str, **kwargs: Any) -> _FakeResponse:
        nonlocal attempts
        attempts += 1
        seen_ranges.append(kwargs.get("headers", {}).get("Range"))
        if attempts == 1:
            raise requests.ConnectionError("corte temporal")
        return _FakeResponse(b"rest", status_code=206)

    monkeypatch.setattr(placsp.requests, "get", fake_get)
    monkeypatch.setattr(placsp.time, "sleep", lambda _: None)
    rec = placsp.download("licitaciones", "202609", base_dir=tmp_path)
    assert attempts == 2
    assert seen_ranges == ["bytes=3-", "bytes=3-"]
    assert (tmp_path / rec.path).read_bytes() == b"PK rest"
