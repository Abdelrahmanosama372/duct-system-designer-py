# Duct System Designer (DSD)

>[!WARNING]
> **No longer maintained — this repository will be archived.**
>
> Development has moved to C++. The requirements evolved to need responsive,
> interactive communication between AutoCAD and the core design logic, and the
> overhead of pyautocad's COM interface made it too slow for that workflow.
> The C++ implementation uses AutoCAD's ObjectARX API for faster CAD model
> rendering and direct integration. Keeping both the AutoCAD adapter and core
> logic in C++ also keeps the project in one language, avoiding FFI bindings or
> communication between separate adapter and core applications.

DSD is a Python tool for automating HVAC ductwork design from AutoCAD drawings.
It turns duct centerlines and air-terminal blocks into connected supply or return
networks, sizes rectangular ducts and fittings, generates 2D plan geometry, and
calculates net sheet-metal area.

## What is implemented

- **Drawing input and topology:** read configured AutoCAD layers, identify system
  roots, split connected lines at junctions and terminals, and aggregate airflow.
- **Duct sizing:** equal-velocity and equal-friction methods with configurable
  dimensions, size increments, and air properties; supplied sizes are preserved.
- **Rectangular fittings:** build component trees with elbows, shoe takeoffs,
  reducers, and endcaps, then size fittings from their connected ducts.
- **Geometry and quantities:** place components, adjust duct lengths, construct
  2D outlines, and calculate per-component and total net sheet-metal area.
- **AutoCAD output:** write geometric primitives and text to configured layers.

The core sizing and geometry logic is separate from the AutoCAD adapter and can
be exercised without a running CAD application. This Python version is incomplete:
weight calculation, visibility/occlusion handling, and terminal component modeling
remain unfinished.

## Setup and basic usage

Use Python 3.12 or later:

```bash
pip install -e '.[test]'
```

Live drawing access requires Windows, AutoCAD with an active drawing, and
pyautocad. Start with [config.yaml](config.yaml) or
[examples/dsd_config.yaml](examples/dsd_config.yaml), and create the configured
input and output layers in AutoCAD.

Draw duct centerlines as LINE entities and use the configured terminal blocks.
System roots need `DSD` XData entries for `system-name` and `system-type`
(`supply` or `return`); terminals need numeric `flow` metadata. Drawing dimensions
are in millimetres, airflow is in CFM, and angles are in radians.

```python
from dsd.adapters.autocad import AutoCad
from dsd.config_builder import ConfigBuilder
from dsd.ductsystem import DuctSystem
from dsd.ductsystem.sizing import EqualFrictionDuctSizer

config = ConfigBuilder("examples/dsd_config.yaml").build()
cad = AutoCad(config.reader, config.writer)
sizer = EqualFrictionDuctSizer(config.sizing)

for topology in cad.analyze_systems():
    system = DuctSystem.from_topology(topology, config.ductsystem, sizer)
    system.size()
```

Sizing builds the dimensioned component tree. Geometry construction and drawing
output are separate steps; see the
[geometry integration tests](integration/test_rectangular_geometry_pipeline.py)
for examples of the placement pipeline.

## Tests and design notes

```bash
pytest -q
```

Tests run without AutoCAD. See [integration/README.md](integration/README.md) for
end-to-end sizing and geometry scenarios, and [design.md](design.md) for design
notes.
