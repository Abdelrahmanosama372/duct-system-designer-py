import pytest

from dsd.analyzers.models import DuctInfo, SystemTopology
from dsd.ductsystem import SystemType
from dsd.geometry.placement import SourceGeometryRepository
from dsd.geometry.primitives import Line, Point


def test_split_segments_are_keyed_by_processed_ids_not_shared_cad_reference():
    first = Line(Point(0, 0), Point(1000, 0), id=0)
    second = Line(Point(1000, 0), Point(2000, 0), id=1)
    topology = SystemTopology(
        "Supply",
        [DuctInfo(0, None, first, 99), DuctInfo(1, 0, second, 99)],
        [],
        SystemType.Supply,
    )
    repo = SourceGeometryRepository.from_topology(topology)
    assert repo.get_line(0).end.x == 1000
    assert repo.get_line(1).start.x == 1000
    assert repo.get_line(0) is not first
    first.end.x = 500
    assert repo.get_line(0).end.x == 1000
    with pytest.raises(ValueError, match="Missing"):
        repo.get_line(99)


def test_repository_rejects_ambiguous_or_inconsistent_ids():
    line = Line(Point(0, 0), Point(1000, 0), id=0)
    with pytest.raises(ValueError, match="keys"):
        SourceGeometryRepository({1: line})
    topology = SystemTopology(
        "Supply", [DuctInfo(1, None, line, 99)], [], SystemType.Supply
    )
    with pytest.raises(ValueError, match="match topology"):
        SourceGeometryRepository.from_topology(topology)
