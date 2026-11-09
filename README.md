# Duct System Designer (DSD)

DSD automates HVAC ductwork design. AutoCAD input/output and per-system topology
analysis, rectangular component tree construction, and standalone duct sizers are
implemented, including parent-first duct sizing and separate reducer/fitting passes.
Net sheet-metal area calculation and rectangular 2D plan geometry are implemented.
Weight calculation and visibility/occlusion handling are pending.

Use Python 3.12 or later. Install with `pip install -e '.[test]'`.
Live AutoCAD access uses pyautocad and requires Windows with AutoCAD running and
an active drawing. Tests use mocked connections and run without AutoCAD.

Use [config.yaml](config.yaml) as the default application configuration, or adapt
[examples/dsd_config.yaml](examples/dsd_config.yaml). Create the
configured layers in AutoCAD yourself. Input coordinates, output coordinates,
and text heights are in millimetres; angles are in radians.

```python
from dsd.adapters.autocad import AutoCad
from dsd.config_builder import ConfigBuilder
from dsd.ductsystem import DuctSystem
from dsd.ductsystem.sizing import EqualFrictionDuctSizer
from dsd.geometry.primitives import Line, Point

config = ConfigBuilder("examples/dsd_config.yaml").build()
cad = AutoCad(config.reader, config.writer)
autocad_input = cad.reader.read()  # lines, blocks, roots; no system membership
topologies = cad.analyze_systems()  # one SystemTopology per root
sizer = EqualFrictionDuctSizer(config.sizing)
systems = [DuctSystem.from_topology(topology, config.ductsystem, sizer) for topology in topologies]
for system in systems:
    system.size()

cad.writer.write_primitive(Line(Point(0, 0), Point(1000, 0)), "duct-output")
cad.writer.write_text("Supply", Point(0, 100), 125, "duct-annotations")

# Explicitly deletes every entity on configured cleanup layers in all layouts:
# cad.writer.clear_output_layers()
```

The reader scans Model Space on the configured input layer. It accepts LINE
entities and block references matching configured terminal block names (including
EffectiveName for dynamic blocks). XData strings under application `DSD` are
parsed at the first `=`; malformed entries and non-string XData are ignored.
Metadata values remain strings. Repeated ordinary keys keep their last value;
repeated `system-name` keys, empty system names, and duplicate system names across
root lines raise `ValueError`.

Root lines carry `system-name=...` and `system-type=supply` or
`system-type=return` under DSD XData. System type is required for topology analysis
and is carried as SystemType through SystemTopology to DuctSystem. Missing or
unsupported types raise TopologyError. System type is not a YAML setting. Roots receive IDs starting at zero, followed
by other lines, then blocks, in drawing enumeration order within each group.
The reader returns `AutoCadInput(lines, blocks, roots)` from `read()`. Roots
reference the same LineInfo objects as the lines collection. The existing separate
line/block accessors and system-name-to-root-ID mapping remain available.
The reader leaves connectivity and membership to the topology analyzer.
Reads share a snapshot; call `cad.reader.refresh()` after editing the drawing.
IDs belong to that snapshot and can change after refresh.

`TopologyAnalyzer(autocad_input).analyze(root)` interprets one system. It discovers
connected source lines, splits at line intersections and terminal insertion points,
and orients segments from inlet to leaves. It reuses the existing geometry
intersection, point-on-segment, and splitting helpers, including their tolerances.
All topology calculations use X and Y only; source Z values are ignored.
Interpreted raw lines lie in the XY plane. Plan crossings connect regardless of Z. Collinear
overlaps, cycles, connections to another root, and ambiguous inlets raise
`TopologyError` (`TopologyConflictError` for multiple roots).

If lines connect to the root start rather than its end, the interpreted root is
reversed. Connections at both root endpoints are ambiguous. An isolated root or a
root with only interior junctions retains its original direction. Source geometry
is never modified. Disconnected lines and blocks are excluded from that system.

Each system receives fresh sequential duct IDs, followed by terminal IDs. Parent
IDs identify upstream ducts; the first duct has parent_id=None. DuctInfo.raw is
the actual split and oriented Line, whose ID matches the duct ID; ref_line_id and
ref_block_id retain the reader's original source references. Duct length comes
from raw geometry. Split segments inherit metadata; optional width, height, and
diameter values are parsed from the corresponding keys as positive numbers.

Terminals attach to the segment arriving at their insertion point, including at
midline cuts and junctions. Ducts may continue downstream of a terminal. A terminal
at the inlet has no upstream segment and raises an error. Each associated terminal
requires finite, nonnegative numeric `flow` metadata. Duct flow sums all downstream
terminal flows, including terminals on the segment endpoint; a terminal-free branch
has zero flow. Neither domain components nor DuctFittingTree objects are built here.

`ConfigBuilder(path).build()` reads the entire YAML once, validates the configured
module sections, and returns reader, writer, ductsystem, and sizing configs. The required
`ductsystem` section contains `material` (`GalvanizedSteel` or `Aluminum`, also
accepting the original spelling `Alminum`) and `pressure_level` (`lowpressure`,
`mediumpressure`, or `highpressure`). It also requires `fittings.takeoff_length`
and `fittings.reducer_length` in mm and `fittings.elbow_inside_radius_ratio`.
`AutoCad.from_yaml()` uses this same builder.

`DuctFittingTreeBuilder(config).build(topology)` produces one component per
SheetMetalNode, with parent nodes and child nodes. The root parent is None.
`DuctSystem.from_topology(topology, config, sizer)` wraps the tree with its system
name, type, configuration, and injected configured sizer. Construction leaves the
tree unsized. Both tree and system expose level_order_traversal() and
preorder_traversal(). Topology duct IDs are retained;
inserted fittings and synthetic ducts receive unique IDs above the topology IDs.
RectangularDuct stores ref_line_id and its scalar length, with no embedded line
geometry. The builder reads DuctInfo.raw without modifying it; positioning will
resolve geometry through the planned source repository.

Ordinary ducts preserve width/height from DuctInfo when both are provided;
otherwise both start unset. Supplying just one dimension raises an error. A single outgoing duct with a direction change gets an elbow with its signed
angle in radians. Its radius is derived from its width and configuration. Branch junctions support a straight continuation
and perpendicular left/right branches. Each side gets its own shoe takeoff as a child of the main duct. A shoe has
only its branch duct as a child; a real main continuation is its sibling. Unsupported angled branch junctions
raise DuctTreeError. Circular ducts are not supported by this rectangular builder.

If the main ends in opposite takeoffs without a straight continuation, the builder
attaches a RectangularEndcap directly to the main duct, alongside the two shoes.
It does not create an extra duct or extend the main length. The geometry stage
will handle any main-duct extension needed for placement.

All components receive system-configured material and pressure level.
`system.size()` executes three independent passes, also callable separately:

1. `size_ducts()` walks in preorder. Supplied width/height pairs are preserved.
   Other ducts use the injected sizer with the nearest upstream duct's sized width
   as their initial guess, skipping intervening fittings. Source lengths remain
   unchanged; endcaps are fittings and are skipped by this pass.
2. `insert_reducers()` inserts reducer nodes between differently sized adjacent
   ducts on the main path. A main reducer and side shoe are siblings under the
   upstream duct. It preserves parent/child links, sibling order, source IDs, and
   unique component IDs. Side branches do not receive reducers merely because they
   differ from the main. A terminal endcap needs no reducer. Repeating the pass
   does not add duplicate reducers.
3. `size_fittings()` assigns dimensions from the sized connected ducts. Reducing
   elbows are unsupported and raise DuctSizingError. Endcaps inherit their parent main duct dimensions. Reducer inlet/outlet dimensions follow connected ducts,
   and their length comes from configuration.

A shoe stores its child-side width/height and configured takeoff_length. Its
45-degree bevel opening, width1, is derived as child width + takeoff_length;
width2 is removed. branch_duct_id identifies its sole branch child, and shoe flow
is that branch's flow. A shoe does not represent the main-flow junction itself. Elbows store no independent radius: inside_radius(ratio) returns
ratio * width and centerline_radius(ratio) returns (ratio + 0.5) * width. Pass
config.ductsystem.fittings.elbow_inside_radius_ratio to these methods.

Terminal components, duct trimming, and weight calculation remain deferred.

Rectangular plan geometry is constructed after system sizing:

```python
from dsd.geometry.placement import SourceGeometryRepository, PlacementContextManager
from dsd.geometry.builders.rectangular import RectangularGeometricRepresentationBuilder
from dsd.ductsystem.visitors import GeometryConstructorVisitor

# Use the topology for this system; processed raw.id keys are local to that system.
repository = SourceGeometryRepository.from_topology(topology)
system = DuctSystem.from_topology(topology, config.ductsystem, sizer)
system.size()
builder = RectangularGeometricRepresentationBuilder(config.ductsystem.fittings)
placement = PlacementContextManager(system.dftree, repository)
geometry = GeometryConstructorVisitor(placement, builder)
representations = geometry.construct()
```

Each GeometricRepresentation contains outline primitives and layout_skeleton lines
in drawing coordinates. Ducts, shoes, and reducers have transverse lines at both
ends. Elbows have two arcs and two end lines; their skeleton is two finite lines
meeting at the source corner. Endcaps have one transverse line and an empty
skeleton. Local models use +X along the component and +Y to its left. The builder
retains normalized_representations by component ID and transforms copies for each
placement; dimension changes invalidate that component's normalized model.

SourceGeometryRepository stores copies of processed DuctInfo.raw lines by raw.id,
which must match the topology duct ID. Original CAD ref_line_id is retained on the
duct for traceability but is not used as the processed repository key: several split
segments can share an original CAD reference.

Geometry construction runs in two passes. First it places fittings using their
parent/child ducts and source axes. Reducer inlets start 1.5 times the parent width
downstream of the original junction, with their full length farther downstream.
Shoes attach to the main side at half its width; their bevel widens downstream for
both supply and return systems. Terminal main ducts extend beyond the original
junction by twice the largest connected shoe's branch width, ending at the endcap.

The second pass connects ducts using the placed fitting skeletons, including the
upstream extension to a downstream-offset reducer. Component duct lengths are
updated; source lines remain unchanged. Use the area visitor afterward to calculate
areas from these adjusted lengths. Repeated construction is stable. Missing sources,
missing fitting layouts, and nonpositive remaining duct lengths raise PlacementError.
Plan elbows require a turn strictly below 180 degrees. No named connection points,
occupancy rectangles, dedicated DuctTrimmer, or visibility/occlusion processing are
implemented in this stage; adjacent end lines remain in both representations.

`AreaCalculatorVisitor` computes net sheet-metal area in m² from mm dimensions:

```python
from dsd.ductsystem.visitors import AreaCalculatorVisitor

areas = AreaCalculatorVisitor(config.ductsystem.fittings)
for node in system.preorder_traversal():
    area_m2 = node.component.accept(areas)
per_component = areas.areas_m2
total_m2 = areas.total_area_m2
```

`visitor.visit(component)` is equivalent to `component.accept(visitor)`. Results
are kept by component ID in the visitor, with no area stored on the components.
Repeated visits update the recorded area; call reset() or create a new visitor for
a different system, because component IDs are local to each system.

Straight ducts include their four side faces; endcaps are single flat plates.
Smooth rectangular elbows include two annular-sector cheeks and the inner/outer
curved faces, using the configured inside-radius multiplier and absolute turn
angle. Shoes include two trapezoidal cheeks, a straight side, and a 45-degree
bevel side. Their inlet and outlet remain open, and no opening is deducted from
the parent duct. Reducers have centered ports and include all four sloping faces,
accounting for width-only, height-only, or simultaneous dimension changes.
Open connection ends, seams, flanges, and fabrication allowances are excluded.
Missing or invalid required dimensions raise AreaCalculationError. Areas use the
component's current length; this visitor does not perform trimming or extension.

Standalone sizers consume SizingContext and return immutable DuctDimension values:

```python
from dsd.ductsystem.sizing import (
    EqualVelocityDuctSizer, EqualFrictionDuctSizer, SizingContext,
)

velocity_sizer = EqualVelocityDuctSizer(config.sizing)
parent_size = velocity_sizer.size_duct(SizingContext(flow=1000))
child_size = velocity_sizer.size_duct(
    SizingContext(flow=500, preferred_width=parent_size.width)
)
friction_size = EqualFrictionDuctSizer(config.sizing).size_duct(SizingContext(flow=1000))
```

Flow is CFM; dimensions are mm; required_velocity is FPM; required_head_loss is
in. w.g./100 ft. Calculations convert to m³/s, m/s, and Pa/m internally. The pressure
conversion uses conventional inches of water. The sizing.air section requires
density_kg_m3, dynamic_viscosity_pa_s, and roughness_mm; all values in the example
are illustrative project settings. DuctSizerConfig stores roughness internally in m.

Each sizer enforces one aspect_ratio: width / height <= aspect_ratio. Roots derive
an initial width using that ratio, round width up to the size increment, and solve
for the corresponding height. Child sizing starts at preferred_width (rounded down
if not already on the grid), then decrements width until the first acceptable
rectangle is found. Heights round upward. Dimensions stay within configured bounds
and use multiples of size_increment anchored at zero. Preferred width is never
increased; an unavailable size raises NoSolutionWithinBounds. Width can be smaller
than height; the acceptance rule is width/height, not max(width,height)/min(...).

Equal velocity uses actual area Q/V. Equal friction first solves for a circular
equivalent diameter using Darcy–Weisbach, f=64/Re below Re=2300, and Colebrook–White
at and above Re=2300, including transitional flow as specified. It then solves the
rectangular height using the equal-friction equivalent-diameter relationship.
The circular search starts at 20 mm and ends at the equivalent of the largest
permitted square. If 20 mm is already sufficient, minimum rectangular constraints
still apply. Rounded equal-friction results are checked against the pressure target.

Diameter and height bisection retain the sufficient upper bound and enforce the
configured diameter_tolerance_mm and max_iterations (default 30). The laminar/
turbulent switch can have a pressure discontinuity: the solver finds a sufficient
size rather than promising exact pressure equality. Colebrook–White uses the
same bisection helper with separate friction_tolerance and friction_max_iterations
settings. NumericalConvergenceError reports exhausted numerical iteration budgets.

Standalone sizers reject zero/negative/nonfinite flow. Endcaps carry zero flow
and are sized from their main duct. An unsized zero-flow duct raises DuctSizingError. Numerical sizers remain independent of component traversal; the
three passes perform tree updates and preserve supplied dimensions.

The writer supports lines, rectangles (four lines), circles, arcs, and single-line
text. Arc sweeps are radians, positive counterclockwise; negative sweeps are
written with reversed endpoints. Full circles use Circle. Dimensions are deferred.
Output layers must exist; missing layers raise `ValueError`. The explicit layer
argument controls output regardless of primitive style. Cleanup is explicit and
includes Model Space and paper layouts; it does not edit reusable block definitions.

Run `pytest -q` for the complete unit and integration suite. Run
`pytest -v integration` for the standalone [duct-system integration scenarios](integration/README.md). Live compatibility
with AutoCAD 2025–2027 requires validation on Windows.

API references: [pyautocad](https://pyautocad.readthedocs.io/en/latest/api.html)
and [AutoCAD ActiveX](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-LT-ActiveX-Reference/files/GUID-864A7E1F-D221-4C83-A4DB-F60C8E56FED6.htm).

Sizing references: [NIST unit conversions](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9),
[NIST Colebrook reference](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=910115),
and [Autodesk equivalent-diameter reference](https://images.autodesk.com/adsk/files/revit_mep_2011_user_guide_en.pdf).
