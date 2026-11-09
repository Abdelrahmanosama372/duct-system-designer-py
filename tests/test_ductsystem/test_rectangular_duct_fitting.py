import pytest

from dsd.ductsystem.models.rectangular import RectangularDuctFitting


def test_unsized_fitting(properties):
    fitting = RectangularDuctFitting(**properties)
    assert fitting.width is None and fitting.height is None
