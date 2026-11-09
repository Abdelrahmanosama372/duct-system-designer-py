"""One shared pyautocad connection for a reader and writer."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .autocad_reader import AutoCadReader
from .autocad_writer import AutoCadWriter
from .reader_config import ReaderConfig
from .writer_config import WriterConfig

if TYPE_CHECKING:
    from dsd.analyzers.models import SystemTopology


class AutoCad:
    def __init__(
        self,
        reader_config: ReaderConfig,
        writer_config: WriterConfig,
        connection: Any = None,
    ) -> None:
        if connection is None:
            # Lazy import keeps configuration and mocked tests usable off Windows.
            from pyautocad import Autocad

            connection = Autocad(create_if_not_exists=False)
        self.connection = connection
        self.reader = AutoCadReader(connection, reader_config)
        self.writer = AutoCadWriter(connection, writer_config)

    @property
    def system_roots(self) -> dict[str, int]:
        self.reader.read_duct_network_lines()
        return dict(self.reader.system_roots)

    def analyze_systems(self) -> list["SystemTopology"]:
        """Analyze each registered root against one complete CAD snapshot."""
        from dsd.analyzers.topology_analyzer import TopologyAnalyzer

        autocad_input = self.reader.read()
        analyzer = TopologyAnalyzer(autocad_input)
        return [analyzer.analyze(root) for root in autocad_input.roots]

    @classmethod
    def from_yaml(cls, path: str | Path, connection: Any = None) -> "AutoCad":
        from dsd.config_builder import ConfigBuilder

        config = ConfigBuilder(path).build()
        return cls(config.reader, config.writer, connection)
