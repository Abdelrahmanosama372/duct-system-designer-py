"""One shared pyautocad connection for a reader and writer."""

from pathlib import Path
from typing import Any

import yaml

from .autocad_reader import AutoCadReader
from .autocad_writer import AutoCadWriter
from .reader_config import ReaderConfig
from .writer_config import WriterConfig


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

    @classmethod
    def from_yaml(cls, path: str | Path, connection: Any = None) -> "AutoCad":
        with Path(path).open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
        return cls(
            ReaderConfig.from_mapping(data), WriterConfig.from_mapping(data), connection
        )
