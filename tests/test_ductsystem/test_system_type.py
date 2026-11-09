import pytest

from dsd.ductsystem import SystemType


@pytest.mark.parametrize(
    "value,expected", [("supply", SystemType.Supply), ("return", SystemType.Return)]
)
def test_supported_system_types(value, expected):
    assert SystemType(value) is expected


def test_unsupported_system_type():
    with pytest.raises(ValueError):
        SystemType("exhaust")
