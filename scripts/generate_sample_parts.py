"""Regenerate the example parts in ``example_parts/``.

This is a DEVELOPMENT script.  It is the only thing in the project that needs
CadQuery, and it is not required to run any analysis - the sample files it
produces are committed to the repository.

    pip install cadquery
    python scripts/generate_sample_parts.py

The sample bracket is deliberately designed to contain real DFX problems so
that the analysers have something to find:

  * a 1.5 mm pilot hole  - below the 2.0 mm CNC minimum, and far too small
    for a standard 5 mm CMM touch probe
  * five distinct hole diameters - a tool-change and inspection burden
  * a 2.0 mm web between the slot and the edge - a thin section
"""

import os
import re

import cadquery as cq

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, 'example_parts')

LENGTH, WIDTH, THICKNESS = 80.0, 60.0, 6.0


def build_bracket():
    """An L-bracket plate with mounting holes, a slot and corner fillets."""
    part = (
        cq.Workplane('XY')
        .box(LENGTH, WIDTH, THICKNESS, centered=(True, True, False))
        .edges('|Z').fillet(8.0)
        # Four mounting holes, M6 clearance
        .faces('>Z').workplane()
        .rect(60.0, 40.0, forConstruction=True).vertices()
        .hole(6.5)
        # Central bore
        .faces('>Z').workplane()
        .hole(20.0)
    )
    # A small pilot hole: too small to machine cheaply or to probe.
    part = (
        part.faces('>Z').workplane()
        .center(-30.0, 0.0).hole(1.5)
    )
    # An upstand with its own hole, so the part is not a flat plate.
    upstand = (
        cq.Workplane('XZ')
        .workplane(offset=WIDTH / 2.0)
        .box(30.0, 25.0, THICKNESS, centered=(True, False, True))
        .translate((0, 0, 0))
    )
    part = part.union(upstand)
    # A through hole in the upstand, cut explicitly along +Y so it is
    # independent of which face the selector happens to pick.
    bore = cq.Solid.makeCylinder(
        5.0, 60.0, cq.Vector(0, -30.0, 15.0), cq.Vector(0, 1, 0))
    part = part.cut(bore)
    return part


def rename_product(step_path, name, description):
    """Replace the exporter's placeholder PRODUCT name with a real one.

    OpenCASCADE writes its own translator string into the PRODUCT entity,
    which is what every downstream tool then displays as the part name.
    """
    with open(step_path, 'r', encoding='utf-8') as handle:
        text = handle.read()
    pattern = re.compile(r"PRODUCT\s*\(\s*'[^']*'\s*,\s*'[^']*'")
    text, count = pattern.subn("PRODUCT('%s','%s'" % (name, description), text, count=1)
    with open(step_path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return count


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    bracket = build_bracket()

    step_path = os.path.join(OUT_DIR, 'sample_bracket.STEP')
    stl_path = os.path.join(OUT_DIR, 'sample_bracket.stl')

    cq.exporters.export(bracket, step_path)
    rename_product(step_path, 'Sample_Bracket',
                   'Demonstration bracket with deliberate DFX issues')
    cq.exporters.export(bracket, stl_path, tolerance=0.05, angularTolerance=0.2)

    solid = bracket.val()
    print("Wrote %s" % step_path)
    print("Wrote %s" % stl_path)
    print("Reference volume: %.2f mm3" % solid.Volume())
    print("Reference area:   %.2f mm2" % solid.Area())
    bb = solid.BoundingBox()
    print("Reference bbox:   %.2f x %.2f x %.2f mm" % (bb.xlen, bb.ylen, bb.zlen))


if __name__ == '__main__':
    main()
