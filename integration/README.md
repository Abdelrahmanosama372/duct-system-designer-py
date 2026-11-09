# Duct-system integration tests

Run only integration tests:

```bash
pytest -v integration
```

Run the complete unit and integration suite:

```bash
pytest -q
```

The tests use real configuration loading, tree construction, numerical sizers,
reducer insertion, and fitting sizing. They start from explicit SystemTopology
inputs and do not require AutoCAD or use mocked sizers.

The fixed settings in [fixtures/duct_system.yaml](fixtures/duct_system.yaml)
keep the cases independent of changes to application defaults. The explicit network builders and scenario tests are in
[test_duct_system_integration.py](test_duct_system_integration.py). Each test
constructs DuctSystem directly, calls size(), and compares the resulting tree
against literal dictionaries. Expected dimension tables sit immediately above
their corresponding test, with component IDs matching its expected tree.
Those expected values are not computed by calling the production sizer inside the
tests. Settings are 25 mm increments, 25–2000 mm dimensions, width/height <= 2,
1000 FPM for equal velocity, and 0.1 in. w.g./100 ft for equal friction.

Both scenarios run for supply and return using both sizing methods:

```text
Main-continuation scenario:
  Main 1000 CFM
    Shoe -> Branch 400 CFM -> Elbow -> Duct 400 CFM
    Reducer -> Main continuation 600 CFM

Terminal-junction scenario:
  Main 1000 CFM
    Left shoe -> Branch 400 CFM
    Right shoe -> Branch 600 CFM
    Endcap
```

Assertions cover exact duct dimensions, parent/child links, unique component IDs,
source references, unmodified input topology, duct lengths, configured fitting
lengths, derived elbow radii and shoe openings, main-continuation reducers,
direct endcap attachment without an extra duct or main-length change, and stable
repeat sizing.

Additional cases verify preservation of supplied parent dimensions, use of parent
width when sizing children, rejection of incomplete dimensions, and rejection of
reducing elbows. The sizing parameter matrix contains 24 integration cases. Two additional tests
check per-component and total net sheet-metal areas for the same main and terminal
networks, using explicit expected areas in m².

Rectangular geometry is checked separately in
[test_rectangular_geometry_pipeline.py](test_rectangular_geometry_pipeline.py).
It uses explicit source coordinates and expected fitting/duct skeleton endpoints,
then repeats the network under rotations and translation. It also verifies terminal
extension, empty endcap skeletons, repeated construction, unchanged repository
lines, and errors when fittings consume the available duct length.
