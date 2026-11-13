"""Validación de NIF españoles (DNI, NIE y NIF de personas jurídicas).

Algoritmos de dígito de control según:
- DNI/NIE: Orden INT/2058/2008 (letra = número módulo 23).
- Personas jurídicas y entidades: Orden EHA/451/2008 (dígito o letra de control).
"""

from __future__ import annotations

import hashlib
import re

DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
CIF_CONTROL_LETTERS = "JABCDEFGHI"

_DNI_RE = re.compile(r"^(\d{8})([A-Z])$")
_NIE_RE = re.compile(r"^([XYZ])(\d{7})([A-Z])$")
_CIF_RE = re.compile(r"^([ABCDEFGHJNPQRSUVW])(\d{7})([0-9A-J])$")
# Personas físicas con NIF especial (K, L, M): misma letra de control que el DNI.
_KLM_RE = re.compile(r"^([KLM])(\d{7})([A-Z])$")

# Tipos que siempre llevan letra de control / siempre dígito (Orden EHA/451/2008).
_CIF_LETTER_ONLY = set("NPQRSW")
_CIF_DIGIT_ONLY = set("ABCDEFGHJUV")


def _cif_control(digits: str) -> int:
    total = 0
    for i, ch in enumerate(digits):
        n = int(ch)
        if i % 2 == 0:  # posiciones impares (1, 3, 5, 7): se duplican
            n *= 2
            n = n // 10 + n % 10
        total += n
    return (10 - total % 10) % 10


def nif_kind(nif: str | None) -> str | None:
    """Devuelve 'DNI', 'NIE', 'CIF' o 'KLM' según el formato, o None si no encaja."""
    if not nif:
        return None
    if _DNI_RE.match(nif):
        return "DNI"
    if _NIE_RE.match(nif):
        return "NIE"
    if _CIF_RE.match(nif):
        return "CIF"
    if _KLM_RE.match(nif):
        return "KLM"
    return None


def is_valid_nif(nif: str | None) -> bool:
    if not nif:
        return False
    if m := _DNI_RE.match(nif):
        return DNI_LETTERS[int(m.group(1)) % 23] == m.group(2)
    if m := _NIE_RE.match(nif):
        number = "XYZ".index(m.group(1)) * 10_000_000 + int(m.group(2))
        return DNI_LETTERS[number % 23] == m.group(3)
    if m := _KLM_RE.match(nif):
        return DNI_LETTERS[int(m.group(2)) % 23] == m.group(3)
    if m := _CIF_RE.match(nif):
        kind, digits, control = m.groups()
        expected = _cif_control(digits)
        as_digit = str(expected)
        as_letter = CIF_CONTROL_LETTERS[expected]
        if kind in _CIF_LETTER_ONLY:
            return control == as_letter
        if kind in _CIF_DIGIT_ONLY:
            return control == as_digit
        return control in (as_digit, as_letter)
    return False


def is_company_nif(nif: str | None) -> bool:
    """True si el NIF corresponde a una persona jurídica o entidad (no a una persona física)."""
    return nif_kind(nif) == "CIF"


def is_personal_nif(nif: str | None) -> bool:
    """True si el NIF tiene formato de persona física (DNI, NIE o K/L/M)."""
    return nif_kind(nif) in ("DNI", "NIE", "KLM")


def mask_nif(nif: str | None) -> str | None:
    """Enmascara un NIF de persona física conservando solo los 4 últimos caracteres."""
    if not nif or not is_personal_nif(nif):
        return nif
    return "*" * max(len(nif) - 4, 1) + nif[-4:]


def pseudonymize_person(nif: str, salt: str = "") -> tuple[str, str]:
    """Genera un identificador y nombre seudónimo determinista para una persona física."""
    digest = hashlib.sha256(f"{salt}:{nif}".encode()).hexdigest()[:10]
    return f"PF-{digest}", f"Persona física ({digest[:8]})"
