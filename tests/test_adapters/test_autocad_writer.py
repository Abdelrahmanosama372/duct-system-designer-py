from math import pi
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from dsd.adapters.autocad import AutoCadWriter, WriterConfig
from dsd.geometry.primitives import Arc, Circle, Line, Point, PrimitiveStyle, Rectangle


def writer(layers=("output",)):
    connection = Mock()
    connection.doc.Layers = [SimpleNamespace(Name=name) for name in layers]
    return AutoCadWriter(connection, WriterConfig(("output",)))


def test_line_uses_explicit_layer_and_preserves_coordinates():
    subject = writer()
    primitive = Line(
        Point(1, 2, 3), Point(4, 5, 6), style=PrimitiveStyle(layer="ignored")
    )
    subject.write_primitive(primitive, "output")
    args = subject.autocad.model.AddLine.call_args.args
    assert list(args[0]) == [1, 2, 3]
    assert list(args[1]) == [4, 5, 6]
    assert subject.autocad.model.AddLine.return_value.Layer == "output"


def test_rectangle_is_four_lines():
    subject = writer()
    entities = [Mock() for _ in range(4)]
    subject.autocad.model.AddLine.side_effect = entities
    subject.write_primitive(Rectangle.from_bounds(Point(0, 0), Point(10, 20)), "output")
    calls = subject.autocad.model.AddLine.call_args_list
    assert [(list(c.args[0]), list(c.args[1])) for c in calls] == [
        ([0, 0, 0], [10, 0, 0]),
        ([10, 0, 0], [10, 20, 0]),
        ([10, 20, 0], [0, 20, 0]),
        ([0, 20, 0], [0, 0, 0]),
    ]
    assert all(entity.Layer == "output" for entity in entities)
    subject.autocad.model.AddPolyline.assert_not_called()


def test_circle():
    subject = writer()
    subject.write_primitive(Circle(Point(10, 20), 30), "output")
    args = subject.autocad.model.AddCircle.call_args.args
    assert list(args[0]) == [10, 20, 0]
    assert args[1] == 30
    assert subject.autocad.model.AddCircle.return_value.Layer == "output"


@pytest.mark.parametrize(
    "sweep, expected", [(pi / 2, (0, pi / 2)), (-pi / 2, (-pi / 2, 0))]
)
def test_arc_radians_and_direction(sweep, expected):
    subject = writer()
    subject.write_primitive(Arc(Point(10, 0), Point(0, 0), sweep), "output")
    args = subject.autocad.model.AddArc.call_args.args
    assert list(args[0]) == [0, 0, 0]
    assert args[1] == 10
    assert args[2:] == pytest.approx(expected)


def test_text():
    subject = writer()
    subject.write_text("Supply", Point(1, 2), 125, "output", rotation=pi / 4)
    args = subject.autocad.model.AddText.call_args.args
    assert args[0] == "Supply"
    assert list(args[1]) == [1, 2, 0]
    assert args[2] == 125
    assert subject.autocad.model.AddText.return_value.Rotation == pi / 4
    assert subject.autocad.model.AddText.return_value.Layer == "output"


@pytest.mark.parametrize(
    "operation",
    [
        lambda w: w.write_primitive(Line(Point(0, 0), Point(1, 1)), "missing"),
        lambda w: w.write_text("test", Point(0, 0), 10, "missing"),
        lambda w: w.clear_output_layers(),
    ],
)
def test_missing_layer_raises_without_mutation(operation):
    subject = writer(layers=())
    with pytest.raises(ValueError, match="does not exist"):
        operation(subject)
    assert subject.autocad.model.mock_calls == []


def test_clear_deletes_only_configured_layers_across_layouts():
    subject = writer()
    output, paper, keep = (
        Mock(Layer="output"),
        Mock(Layer="OUTPUT"),
        Mock(Layer="input"),
    )
    subject.autocad.doc.Layouts = [
        SimpleNamespace(Block=[output, keep]),
        SimpleNamespace(Block=[paper]),
    ]
    subject.clear_output_layers()
    output.Delete.assert_called_once_with()
    paper.Delete.assert_called_once_with()
    keep.Delete.assert_not_called()


@pytest.mark.parametrize(
    "primitive",
    [
        Circle(Point(0, 0), 0),
        Arc(Point(0, 0), Point(0, 0), 1),
        Arc(Point(1, 0), Point(0, 0), 0),
        Arc(Point(1, 0), Point(0, 0), 2 * pi),
    ],
)
def test_invalid_geometry_is_rejected(primitive):
    subject = writer()
    with pytest.raises(ValueError):
        subject.write_primitive(primitive, "output")
    assert subject.autocad.model.mock_calls == []


@pytest.mark.parametrize(
    "text,height,rotation",
    [("a\nb", 10, 0), ("test", 0, 0), ("test", 10, float("nan"))],
)
def test_invalid_text_is_rejected(text, height, rotation):
    subject = writer()
    with pytest.raises(ValueError):
        subject.write_text(text, Point(0, 0), height, "output", rotation)
    subject.autocad.model.AddText.assert_not_called()


def test_unsupported_primitive():
    with pytest.raises(TypeError, match="Unsupported"):
        writer().write_primitive(Point(0, 0), "output")


def test_empty_cleanup_config_does_not_access_layouts():
    connection = Mock()
    subject = AutoCadWriter(connection, WriterConfig())
    subject.clear_output_layers()
    assert connection.mock_calls == []
