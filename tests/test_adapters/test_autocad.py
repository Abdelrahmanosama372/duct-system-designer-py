import sys
from types import SimpleNamespace
from unittest.mock import Mock

from dsd.adapters.autocad import AutoCad, ReaderConfig, WriterConfig


def test_shared_injected_connection():
    connection = Mock()
    subject = AutoCad(ReaderConfig("input"), WriterConfig(), connection)
    assert subject.connection is connection
    assert subject.reader.autocad is connection
    assert subject.writer.autocad is connection


def test_default_connection_attaches_without_starting_autocad(monkeypatch):
    factory = Mock()
    monkeypatch.setitem(sys.modules, "pyautocad", SimpleNamespace(Autocad=factory))
    subject = AutoCad(ReaderConfig("input"), WriterConfig())
    factory.assert_called_once_with(create_if_not_exists=False)
    assert subject.connection is factory.return_value


def test_from_yaml_and_multiple_system_discovery():
    connection = Mock()
    def root(name):
        return SimpleNamespace(Layer="duct-network", ObjectName="AcDbLine",
            StartPoint=(0, 0, 0), EndPoint=(1, 1, 0),
            GetXData=Mock(return_value=([1000], [f"system-name={name}"])))
    connection.iter_objects.return_value = [root("A"), root("B")]
    subject = AutoCad.from_yaml("examples/dsd_config.yaml", connection)
    assert subject.system_roots == {"A": 0, "B": 1}
    roots = subject.system_roots
    roots.clear()
    assert subject.system_roots == {"A": 0, "B": 1}
