from dataclasses import FrozenInstanceError

import pytest

from dsd.ductsystem.sizing import DuctDimension, SizingContext


@pytest.mark.parametrize("flow", [0, -1, True, float("nan"), float("inf")])
def test_invalid_flow(flow):
    with pytest.raises(ValueError):
        SizingContext(flow)


@pytest.mark.parametrize("width", [0, -1, True, float("nan"), float("inf")])
def test_invalid_preferred_width(width):
    with pytest.raises(ValueError):
        SizingContext(100, width)


def test_immutable_context_and_result():
    with pytest.raises(FrozenInstanceError):
        SizingContext(100).flow = 200
    with pytest.raises(FrozenInstanceError):
        DuctDimension(200, 100).width = 300
