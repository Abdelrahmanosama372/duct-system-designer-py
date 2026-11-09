"""Interpreted information for a single rooted duct system."""

from dataclasses import dataclass

from dsd.system_type import SystemType

from .air_terminal_info import AirTerminalInfo
from .duct_info import DuctInfo


@dataclass
class SystemTopology:
    system_name: str
    duct_infos: list[DuctInfo]
    air_terminal_infos: list[AirTerminalInfo]
    system_type: SystemType
