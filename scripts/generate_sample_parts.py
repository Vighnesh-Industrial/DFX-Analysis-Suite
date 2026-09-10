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
  * a thin web between the corner mounting holes and the filleted edge
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
    # Start well outside the upstand (which spans y -33..-27) so the bore
    # goes right through instead of leaving a blind pocket floor.
    bore = cq.Solid.makeCylinder(
        5.0, 80.0, cq.Vector(0, -40.0, 15.0), cq.Vector(0, 1, 0))
    part = part.cut(bore)
    return part


def build_housing():
    """A moulded housing: tapered (drafted) walls, shelled, with fillets.

    Exercises the draft-angle measurement - the 2 degree taper becomes
    conical faces in the STEP file.
    """
    part = (
        cq.Workplane('XY')
        .rect(60.0, 40.0)
        .extrude(20.0, taper=2.0)
        .faces('>Z').shell(-2.0)
    )
    return part


def build_assembly():
    """Three parts in one STEP file, exercising the placement transforms.

    The bracket is both translated and rotated, so a reader that ignores
    placement - or that only handles translation - gets a visibly wrong
    envelope. Assembled extents are 60 x 40 x 28 mm:
      base plate  60 x 40 x  5 at the origin
      top cover   50 x 30 x  3 sitting on the plate at z = 5
      post        10 x 10 x 20 rotated 90 deg about X, standing at z = 8
    """
    plate = cq.Workplane('XY').box(60.0, 40.0, 5.0, centered=(True, True, False))
    cover = cq.Workplane('XY').box(50.0, 30.0, 3.0, centered=(True, True, False))
    post = cq.Workplane('XY').box(10.0, 20.0, 10.0, centered=(True, False, False))

    assembly = cq.Assembly(name='Sample_Assembly')
    assembly.add(plate, name='base_plate', loc=cq.Location(cq.Vector(0, 0, 0)))
    assembly.add(cover, name='top_cover', loc=cq.Location(cq.Vector(0, 0, 5.0)))
    assembly.add(post, name='riser_post',
                 loc=cq.Location(cq.Vector(0, 0, 8.0), cq.Vector(1, 0, 0), 90))
    return assembly


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

    housing_path = os.path.join(OUT_DIR, 'sample_housing.STEP')
    cq.exporters.export(build_housing(), housing_path)
    rename_product(housing_path, 'Sample_Housing',
                   'Moulded housing with 2 degree draft')
    print("Wrote %s" % housing_path)

    assembly_path = os.path.join(OUT_DIR, 'sample_assembly.STEP')
    build_assembly().save(assembly_path)
    print("Wrote %s" % assembly_path)

    solid = bracket.val()
    print("Wrote %s" % step_path)
    print("Wrote %s" % stl_path)
    print("Reference volume: %.2f mm3" % solid.Volume())
    print("Reference area:   %.2f mm2" % solid.Area())
    bb = solid.BoundingBox()
    print("Reference bbox:   %.2f x %.2f x %.2f mm" % (bb.xlen, bb.ylen, bb.zlen))


if __name__ == '__main__':
    main()
