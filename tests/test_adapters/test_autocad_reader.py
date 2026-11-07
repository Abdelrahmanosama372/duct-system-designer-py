from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from dsd.adapters.autocad import AutoCadReader, ReaderConfig


def line(*entries, layer="input", kind="AcDbLine"):
    return SimpleNamespace(
        Layer=layer, ObjectName=kind, StartPoint=(1, 2, 3), EndPoint=(4, 5, 6),
        GetXData=Mock(return_value=([1001] + [1000] * len(entries), ["DSD", *entries])),
    )


def block(name="DIFFUSER", layer="input"):
    return SimpleNamespace(
        Layer=layer, ObjectName="AcDbBlockReference", Name="*U123", EffectiveName=name,
        InsertionPoint=(10, 20, 0), GetXData=Mock(return_value=(None, None)),
    )


def reader(entities):
    connection = Mock()
    connection.iter_objects.return_value = entities
    return AutoCadReader(connection, ReaderConfig("input", ("DIFFUSER",)))


def test_filters_model_space_and_assigns_root_ids_first():
    entities = [line("flow=100"), block(), line("system-name=Supply"),
                line("system-name=Return"), line(layer="other"),
                line(kind="AcDbPolyline"), block("UNKNOWN"), block(layer="other")]
    subject = reader(entities)
    blocks = subject.read_duct_network_blocks()
    lines = subject.read_duct_network_lines()
    assert subject.system_roots == {"Supply": 0, "Return": 1}
    assert [info.raw_line.id for info in lines] == [0, 1, 2]
    assert [info.raw_block.id for info in blocks] == [3]
    assert lines[2].metadata == {"flow": "100"}
    assert lines[0].raw_line.start.to_list3d() == [1, 2, 3]
    assert blocks[0].raw_block.center.to_list3d() == [10, 20, 0]
    assert blocks[0].raw_block.name == "DIFFUSER"
    subject.autocad.iter_objects.assert_called_once_with(block=subject.autocad.model)
    entities[0].GetXData.assert_called_once_with("DSD")


def test_metadata_only_accepts_key_value_strings():
    entity = line()
    entity.GetXData.return_value = (
        [1001, 1000, 1000, 1000, 1040, 1000, 1000, 1000],
        ["DSD", "bad", "flow=100", "expression=a=b", 42, "=empty", "flow=200", 9],
    )
    assert reader([entity]).read_duct_network_lines()[0].metadata == {
        "flow": "200", "expression": "a=b",
    }


@pytest.mark.parametrize("entities", [
    [line("system-name=A"), line("system-name=A")],
    [line("system-name=A", "system-name=B")],
    [line("system-name=")],
])
def test_rejects_invalid_system_names(entities):
    with pytest.raises(ValueError, match="system-name"):
        reader(entities).read_duct_network_lines()


def test_absent_xdata_and_no_roots_are_supported():
    entity = line()
    entity.GetXData.return_value = (None, None)
    subject = reader([entity])
    assert subject.read_duct_network_lines()[0].raw_line.id == 0
    assert subject.system_roots == {}
    assert subject.read_duct_network_blocks() == []


def test_refresh_reloads_snapshot():
    subject = reader([line("system-name=A")])
    subject.read_duct_network_lines()
    subject.autocad.iter_objects.return_value = [line("system-name=B")]
    subject.refresh()
    assert subject.system_roots == {"B": 0}
    assert subject.read_duct_network_lines()[0].metadata == {"system-name": "B"}


def test_com_errors_are_not_silently_ignored():
    entity = line()
    entity.GetXData.side_effect = RuntimeError("COM failed")
    with pytest.raises(RuntimeError, match="COM failed"):
        reader([entity]).read_duct_network_lines()


def test_block_name_falls_back_to_name():
    entity = block()
    del entity.EffectiveName
    entity.Name = "diffuser"
    entity.Layer = "INPUT"
    assert len(reader([entity]).read_duct_network_blocks()) == 1
