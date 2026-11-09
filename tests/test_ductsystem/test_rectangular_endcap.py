import pytest

from dsd.ductsystem.models.rectangular import RectangularDuctFitting, RectangularEndcap


def test_endcap_is_unsized_fitting(properties):
    cap = RectangularEndcap(**properties)
    assert isinstance(cap, RectangularDuctFitting)
    assert cap.width is None and cap.height is None
