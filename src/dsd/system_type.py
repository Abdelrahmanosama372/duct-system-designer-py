"""System classifications shared by topology and duct-system models."""

from enum import StrEnum


class SystemType(StrEnum):
    Supply = "supply"
    Return = "return"
