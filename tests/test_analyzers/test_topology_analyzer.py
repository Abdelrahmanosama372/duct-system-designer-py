from copy import deepcopy

import pytest

from dsd.adapters.autocad.models import AutoCadInput, BlockInfo, LineInfo
from dsd.analyzers import TopologyAnalyzer, TopologyConflictError, TopologyError
from dsd.geometry.primitives import Block, Line, Point
from dsd.system_type import SystemType


def line(identifier, start, end, **metadata):
    return LineInfo(Line(Point(*start), Point(*end), id=identifier), metadata)


def root(identifier=100, start=(0, 0), end=(100, 0), name="Supply", **metadata):
    return line(
        identifier,
        start,
        end,
        **{"system-name": name, "system-type": "supply", **metadata}
    )


def terminal(identifier, position, flow="100", **metadata):
    return BlockInfo(
        Block("DIFFUSER", Point(*position), id=identifier), {"flow": flow, **metadata}
    )


def analyze(lines, blocks=(), roots=None):
    roots = roots if roots is not None else [lines[0]]
    return TopologyAnalyzer(AutoCadInput(lines, list(blocks), roots)).analyze(roots[0])


def test_one_system_preserves_source_references_and_assigns_new_ids():
    inlet = root(width="400", height="200", flow="999")
    child = line(900, (100, 0), (200, 0), diameter="200")
    result = analyze([inlet, child], [terminal(500, (200, 0), "125")])
    assert result.system_name == "Supply"
    assert [d.id for d in result.duct_infos] == [0, 1]
    assert [d.raw.id for d in result.duct_infos] == [0, 1]
    assert [d.parent_id for d in result.duct_infos] == [None, 0]
    assert [d.ref_line_id for d in result.duct_infos] == [100, 900]
    assert [d.flow for d in result.duct_infos] == [125, 125]
    assert [d.length for d in result.duct_infos] == [100, 100]
    assert result.duct_infos[0].width == 400
    assert result.duct_infos[0].height == 200
    assert result.duct_infos[1].diameter == 200
    air = result.air_terminal_infos[0]
    assert (air.id, air.parent_id, air.ref_block_id, air.flow) == (2, 1, 500, 125)


def test_multiple_independent_systems_exclude_unrelated_entities():
    a = root()
    b = root(200, (0, 1000), (100, 1000), name="Return")
    a_child = line(300, (100, 0), (200, 0))
    unrelated = line(400, (5000, 5000), (5100, 5000))
    data = AutoCadInput(
        [a, b, a_child, unrelated],
        [
            terminal(501, (200, 0), "25"),
            terminal(502, (100, 1000), "50"),
            terminal(503, (5100, 5000), "75"),
        ],
        [a, b],
    )
    analyzer = TopologyAnalyzer(data)
    results = [analyzer.analyze(r) for r in data.roots]
    assert [[d.ref_line_id for d in s.duct_infos] for s in results] == [
        [100, 300],
        [200],
    ]
    assert [[t.ref_block_id for t in s.air_terminal_infos] for s in results] == [
        [501],
        [502],
    ]
    assert [s.duct_infos[0].flow for s in results] == [25, 50]
    assert [s.duct_infos[0].id for s in results] == [0, 0]


def test_midline_terminal_splits_and_attaches_to_upstream_segment():
    inlet = root(end=(300, 0), width="400")
    result = analyze(
        [inlet], [terminal(400, (100, 0), "30"), terminal(401, (300, 0), "70")]
    )
    assert [(d.raw.start.x, d.raw.end.x) for d in result.duct_infos] == [
        (0, 100),
        (100, 300),
    ]
    assert [d.flow for d in result.duct_infos] == [100, 70]
    assert [t.parent_id for t in result.air_terminal_infos] == [0, 1]
    assert [d.ref_line_id for d in result.duct_infos] == [100, 100]
    assert all(d.metadata == inlet.metadata for d in result.duct_infos)
    assert all(d.width == 400 for d in result.duct_infos)


def test_t_junction_splits_source_line_and_sums_branch_flows():
    inlet = root(end=(300, 0))
    branch = line(200, (100, 100), (100, 0))  # deliberately backwards
    result = analyze(
        [inlet, branch],
        [terminal(400, (300, 0), "40"), terminal(401, (100, 100), "60")],
    )
    assert len(result.duct_infos) == 3
    assert [d.parent_id for d in result.duct_infos] == [None, 0, 0]
    assert result.duct_infos[0].flow == 100
    assert sorted(d.flow for d in result.duct_infos[1:]) == [40, 60]
    assert result.duct_infos[2].raw.end.to_list3d() == [100, 100, 0]


def test_crossing_splits_both_source_lines():
    inlet = root(end=(300, 0))
    crossing = line(200, (100, -100), (100, 100))
    result = analyze(
        [inlet, crossing],
        [terminal(400, (100, 100), "10"), terminal(401, (100, -100), "20")],
    )
    assert len(result.duct_infos) == 4
    assert result.duct_infos[0].flow == 30
    assert [d.parent_id for d in result.duct_infos] == [None, 0, 0, 0]


def test_flip_root_and_children_without_mutating_input():
    inlet = root(start=(100, 0), end=(0, 0))
    child = line(200, (200, 0), (100, 0))
    data = AutoCadInput([inlet, child], [terminal(400, (200, 0))], [inlet])
    original = deepcopy(data)
    analyzer = TopologyAnalyzer(data)
    for _ in range(2):
        result = analyzer.analyze(inlet)
        assert [(d.raw.start.x, d.raw.end.x) for d in result.duct_infos] == [
            (0, 100),
            (100, 200),
        ]
        assert [d.flow for d in result.duct_infos] == [100, 100]
    assert data.lines == original.lines
    assert [info.raw_line.id for info in data.lines] == [100, 200]
    assert data.blocks[0].raw_block.to_json() == original.blocks[0].raw_block.to_json()
    assert data.blocks[0].raw_block.id == original.blocks[0].raw_block.id
    assert data.blocks[0].metadata == original.blocks[0].metadata
    result.duct_infos[0].metadata["extra"] = "new"
    assert "extra" not in inlet.metadata


def test_terminal_at_junction_uses_unique_upstream_parent_once():
    inlet = root()
    result = analyze(
        [inlet, line(200, (100, 0), (200, 0)), line(300, (100, 0), (100, 100))],
        [terminal(400, (100, 0), "25")],
    )
    assert len(result.air_terminal_infos) == 1
    assert result.air_terminal_infos[0].parent_id == 0
    assert [d.flow for d in result.duct_infos] == [25, 0, 0]


def test_another_registered_root_is_a_conflict():
    a, b = root(), root(200, (200, 0), (300, 0), name="Return")
    middle = line(300, (100, 0), (200, 0))
    for source in [a, b]:
        with pytest.raises(TopologyConflictError, match="connects to root"):
            TopologyAnalyzer(AutoCadInput([a, middle, b], [], [a, b])).analyze(source)


def test_cycle_terminates_with_error():
    inlet = root()
    cycle = [
        line(200, (100, 0), (200, 0)),
        line(300, (200, 0), (150, 100)),
        line(400, (150, 100), (100, 0)),
    ]
    with pytest.raises(TopologyError, match="Cyclic"):
        analyze([inlet, *cycle])


def test_root_with_connections_at_both_endpoints_is_ambiguous():
    with pytest.raises(TopologyError, match="both endpoints"):
        analyze([root(), line(200, (-100, 0), (0, 0)), line(300, (100, 0), (200, 0))])


def test_overlapping_lines_are_rejected():
    with pytest.raises(TopologyError, match="Overlapping"):
        analyze([root(end=(200, 0)), line(200, (100, 0), (300, 0))])


def test_repeated_geometry_is_rejected():
    with pytest.raises(TopologyError, match="Overlapping"):
        analyze([root(), line(200, (0, 0), (100, 0))])


def test_z_difference_does_not_disconnect_xy_crossing():
    result = analyze([root(), line(200, (50, -100, 100), (50, 100, 100))])
    assert len(result.duct_infos) == 4


def test_intersections_and_terminals_ignore_all_z_values():
    result = analyze(
        [
            root(start=(0, 0, 100), end=(200, 0, 100)),
            line(200, (100, 0, 800), (100, 100, -200)),
        ],
        [terminal(400, (100, 100, 9999))],
    )
    assert len(result.duct_infos) == 3
    assert all(d.raw.start.z == 0 and d.raw.end.z == 0 for d in result.duct_infos)
    assert result.duct_infos[0].flow == 100


@pytest.mark.parametrize("flow", ["bad", "nan", "inf", "-1"])
def test_invalid_terminal_flow_is_reported(flow):
    with pytest.raises(TopologyError, match="flow"):
        analyze([root()], [terminal(400, (100, 0), flow)])


def test_missing_terminal_flow_is_reported():
    block = terminal(400, (100, 0))
    block.metadata.clear()
    with pytest.raises(TopologyError, match="flow"):
        analyze([root()], [block])


def test_unrelated_terminal_metadata_is_not_interpreted():
    result = analyze([root()], [terminal(400, (1000, 1000), "invalid")])
    assert result.air_terminal_infos == []
    assert result.duct_infos[0].flow == 0


def test_terminal_at_inlet_is_ambiguous():
    with pytest.raises(TopologyError, match="no upstream"):
        analyze([root()], [terminal(400, (0, 0))])


def test_unregistered_root_is_rejected():
    inlet = root()
    with pytest.raises(TopologyError, match="not a registered"):
        TopologyAnalyzer(AutoCadInput([inlet], [], [])).analyze(inlet)


def test_zero_length_root_is_rejected():
    with pytest.raises(TopologyError, match="Zero-length"):
        analyze([root(end=(0, 0))])


def test_duplicate_source_ids_are_rejected():
    with pytest.raises(TopologyError, match="IDs must be unique"):
        analyze([root(), line(100, (100, 0), (200, 0))])


def test_long_chain_uses_iterative_traversal():
    inlet = root()
    lines = [inlet] + [
        line(100 + n, (n * 100, 0), ((n + 1) * 100, 0)) for n in range(1, 120)
    ]
    result = analyze(lines, [terminal(500, (12000, 0), "10")])
    assert len(result.duct_infos) == 120
    assert all(d.flow == 10 for d in result.duct_infos)


def test_overlapping_roots_report_a_system_conflict():
    a = root(end=(200, 0))
    b = root(200, (100, 0), (300, 0), name="Return")
    with pytest.raises(TopologyConflictError):
        TopologyAnalyzer(AutoCadInput([a, b], [], [a, b])).analyze(a)


def test_disconnected_cycle_is_ignored():
    cycle = [
        line(200, (1000, 1000), (1100, 1000)),
        line(300, (1100, 1000), (1050, 1100)),
        line(400, (1050, 1100), (1000, 1000)),
    ]
    assert len(analyze([root(), *cycle]).duct_infos) == 1


def test_multiple_terminals_at_same_position_are_counted_once_each():
    result = analyze(
        [root()], [terminal(400, (100, 0), "25"), terminal(401, (100, 0), "75")]
    )
    assert len(result.duct_infos) == 1
    assert len(result.air_terminal_infos) == 2
    assert result.duct_infos[0].flow == 100


def test_lengths_and_root_direction_ignore_z_without_mutating_source():
    inlet = root(start=(100, 0, 300), end=(0, 0, -100))
    child = line(200, (100, 0, -900), (200, 0, 900))
    result = analyze([inlet, child], [terminal(400, (200, 0, 5000), "25")])
    assert [duct.length for duct in result.duct_infos] == [100, 100]
    assert [duct.flow for duct in result.duct_infos] == [25, 25]
    assert result.duct_infos[0].raw.start.to_list3d() == [0, 0, 0]
    assert inlet.raw_line.start.to_list3d() == [100, 0, 300]
    assert child.raw_line.end.to_list3d() == [200, 0, 900]


def test_nearby_terminal_is_snapped_to_line_in_xy():
    result = analyze([root(end=(200, 0))], [terminal(400, (100, 0.5, 900), "25")])
    assert len(result.duct_infos) == 2
    assert result.duct_infos[0].raw.end.to_list3d() == [100, 0, 0]
    assert result.air_terminal_infos[0].parent_id == 0


@pytest.mark.parametrize(
    "value,expected", [("supply", SystemType.Supply), ("return", SystemType.Return)]
)
def test_system_type_is_read_from_root_xdata(value, expected):
    inlet = root(**{"system-type": value})
    assert analyze([inlet]).system_type is expected


@pytest.mark.parametrize("value", [None, "", "exhaust", "Supply"])
def test_invalid_or_missing_root_system_type_is_reported(value):
    inlet = root()
    if value is None:
        del inlet.metadata["system-type"]
    else:
        inlet.metadata["system-type"] = value
    with pytest.raises(TopologyError, match="system-type"):
        analyze([inlet])
