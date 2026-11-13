import pytest

from pipelines.quality.nif import is_company_nif, is_personal_nif, is_valid_nif, mask_nif, nif_kind, pseudonymize_person
from pipelines.transform.codice import normalize_nif


@pytest.mark.parametrize(
    "nif",
    [
        "12345678Z",  # DNI
        "X1234567L",  # NIE
        "A28015865",  # sociedad anónima, control numérico
        "P3803500B",  # entidad local, control con letra (dato real de PLACSP)
        "G96236443",  # asociación/mutua (dato real de PLACSP)
        "S2826011E",  # órgano de la Administración del Estado
    ],
)
def test_valid(nif: str) -> None:
    assert is_valid_nif(nif)


@pytest.mark.parametrize("nif", ["12345678A", "A28015866", "P3803500C", "X1234567A", "", None, "336502", "ABC"])
def test_invalid(nif: str | None) -> None:
    assert not is_valid_nif(nif)


def test_kinds() -> None:
    assert nif_kind("12345678Z") == "DNI"
    assert nif_kind("Y1234567X") == "NIE"
    assert nif_kind("B67138503") == "CIF"
    assert nif_kind("336502") is None
    assert is_company_nif("B67138503")
    assert not is_company_nif("12345678Z")


def test_normalize() -> None:
    assert normalize_nif(" b-67.138.503 ") == "B67138503"
    assert normalize_nif("ESB67138503") == "B67138503"
    assert normalize_nif("") is None


def test_personal_nif_mask_and_pseudonymize() -> None:
    assert is_personal_nif("12345678Z")
    assert is_personal_nif("X1234567L")
    assert not is_personal_nif("B67138503")
    assert mask_nif("12345678Z") == "*****678Z"
    assert mask_nif("B67138503") == "B67138503"
    pid1, pname1 = pseudonymize_person("12345678Z", salt="tfm")
    pid2, pname2 = pseudonymize_person("12345678Z", salt="tfm")
    assert pid1 == pid2 and pid1.startswith("PF-")
    assert pname1 == pname2 and pname1.startswith("Persona física (")
    assert "12345678Z" not in pid1 and "12345678Z" not in pname1
