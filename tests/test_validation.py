
import pytest

from server import validate_district_and_limit


def test_valid_district():
    district, limit = validate_district_and_limit(
        "Korba",
        7
    )

    assert district == "Korba"
    assert limit == 7


def test_district_trailing_spaces():
    district, limit = validate_district_and_limit(
        "  Korba  ",
        7
    )

    assert district == "Korba"


def test_empty_district():
    with pytest.raises(ValueError):
        validate_district_and_limit("", 7)


def test_invalid_limit():
    with pytest.raises(ValueError):
        validate_district_and_limit("Korba", 0)


def test_limit_exceeds_maximum():
    with pytest.raises(ValueError):
        validate_district_and_limit("Korba", 500)


def test_boolean_limit():
    with pytest.raises(ValueError):
        validate_district_and_limit("Korba", True)
