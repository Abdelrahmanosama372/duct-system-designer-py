import pytest

from dsd.ductsystem.models import SheetMetalComponent


def test_common_properties(properties):
    component = SheetMetalComponent(**properties)
    assert component.flow == 100
    assert component.id == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("flow", -1),
        ("flow", float("nan")),
        ("id", -1),
        ("material", "steel"),
        ("pressure_level", "low"),
    ],
)
def test_invalid_component_properties(properties, field, value):
    with pytest.raises(ValueError):
        SheetMetalComponent(**{**properties, field: value})
