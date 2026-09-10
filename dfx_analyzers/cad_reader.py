"""CAD file reader: extracts real geometry facts from CAD files.

This module is intentionally dependency-free (standard library only) so that
the analysis core installs and runs anywhere Python runs.  It supports:

  * STEP (.step / .stp) - ISO 10303-21 part 21 text files.  Parsed directly:
    bounding box, cylindrical/conical/toroidal surface radii, face and solid
    counts, units and product name.
  * STL (.stl)          - ASCII and binary meshes.  Exact volume, surface
    area, bounding box and a watertightness check.

Formats that cannot be read without vendor software (Creo .prt/.asm,
SolidWorks .sldprt/.sldasm, IGES) are reported honestly as unreadable with
guidance, rather than silently producing an empty analysis.
"""

import math
import os
import re
import struct
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Result container
# --------------------------------------------------------------------------

READABLE_EXTENSIONS = {'.step', '.stp', '.stl'}

RECOGNISED_EXTENSIONS = {
    '.step': 'STEP', '.stp': 'STEP', '.stl': 'STL',
    '.iges': 'IGES', '.igs': 'IGES',
    '.prt': 'Creo/NX part', '.asm': 'Creo/NX assembly',
    '.sldprt': 'SolidWorks part', '.sldasm': 'SolidWorks assembly',
    '.fcstd': 'FreeCAD document',
}


@dataclass
class CADGeometry:
    """Measured facts about a CAD file.

    Every field is either a real measurement taken from the file or ``None``.
    ``None`` means "not measurable from this file" - it never means zero.
    """

    file_path: str = ''
    file_name: str = ''
    name: str = None
    file_format: str = 'UNKNOWN'
    readable: bool = False
    read_notes: list = field(default_factory=list)

    # Identification
    product_name: str = None
    schema: str = None
    units: str = None
    unit_scale_mm: float = 1.0

    # Bounding box, in millimetres
    bbox_min: tuple = None
    bbox_max: tuple = None

    # Topology / entity counts (STEP)
    point_count: int = 0
    face_count: int = 0
    plane_count: int = 0
    solid_count: int = 0
    shell_count: int = 0
    cylinder_radii: list = field(default_factory=list)
    cone_count: int = 0
    torus_minor_radii: list = field(default_factory=list)
    sphere_count: int = 0
    bspline_surface_count: int = 0

    # Assembly structure (STEP)
    assembly_instance_count: int = 0
    components_placed: bool = False
    # Per-component geometry, measured separately, for an assembly.
    components: list = field(default_factory=list, repr=False)
    distinct_product_count: int = 0

    # Measured draft angles (STEP conical faces), degrees from the axis
    draft_angles_deg: list = field(default_factory=list)

    # Outward normals of the planar faces, for draft measurement
    plane_normals: list = field(default_factory=list, repr=False)
    closed_shell_count: int = 0

    # Wall thickness, measured by ray casting through a mesh
    min_wall_thickness_mm: float = None
    wall_thickness_rays: int = 0

    # Mesh measurements (STL)
    triangles: list = field(default_factory=list, repr=False)
    triangle_count: int = 0
    volume_mm3: float = None
    surface_area_mm2: float = None
    is_watertight: bool = None

    # ---------------------------------------------------------------- helpers

    @property
    def dimensions(self):
        """(dx, dy, dz) of the bounding box in mm, or None."""
        if self.bbox_min is None or self.bbox_max is None:
            return None
        return tuple(round(hi - lo, 4) for lo, hi in zip(self.bbox_min, self.bbox_max))

    @property
    def min_dimension(self):
        dims = self.dimensions
        return min(dims) if dims else None

    @property
    def max_dimension(self):
        dims = self.dimensions
        return max(dims) if dims else None

    @property
    def slenderness(self):
        """Ratio of longest to shortest bounding-box edge."""
        dims = self.dimensions
        if not dims or min(dims) <= 0:
            return None
        return max(dims) / min(dims)

    @property
    def cylindrical_diameters(self):
        """Distinct cylindrical-surface diameters in mm, rounded to 0.01.

        A cylindrical face may be a hole, a boss, or an external corner
        round - a STEP file does not say which without full topology
        traversal.  These are reported as *features*, not as holes.
        """
        return sorted({round(r * 2, 2) for r in self.cylinder_radii if r > 0})

    @property
    def min_cylindrical_diameter(self):
        d = self.cylindrical_diameters
        return d[0] if d else None

    @property
    def fillet_radii(self):
        return sorted({round(r, 2) for r in self.torus_minor_radii if r > 0})

    def wall_draft_angles(self, pull=(0.0, 0.0, 1.0), wall_limit_deg=80.0):
        """Draft angle of every wall face, in degrees from the pull direction.

        0 degrees is a wall exactly parallel to the pull direction, i.e. no
        draft at all. Faces steeper than ``wall_limit_deg`` are floors and
        ceilings rather than walls, and are excluded.

        Returns an empty list when the file carries no face normals.
        """
        length = math.sqrt(sum(component ** 2 for component in pull))
        if length == 0:
            return []
        unit = [component / length for component in pull]

        angles = []
        for normal in self.plane_normals:
            magnitude = math.sqrt(sum(component ** 2 for component in normal))
            if magnitude == 0:
                continue
            cosine = abs(sum(a * b for a, b in zip(normal, unit))) / magnitude
            cosine = max(-1.0, min(1.0, cosine))
            draft = 90.0 - math.degrees(math.acos(cosine))
            if draft < wall_limit_deg:
                angles.append(draft)

        # A conical wall's half-angle is its draft angle directly.
        for half_angle in self.draft_angles_deg:
            if half_angle < wall_limit_deg:
                angles.append(half_angle)
        return sorted(round(a, 2) for a in angles)

    def undrafted_wall_count(self, minimum_deg=1.0, pull=(0.0, 0.0, 1.0)):
        """How many wall faces have less draft than ``minimum_deg``."""
        return sum(1 for a in self.wall_draft_angles(pull) if a < minimum_deg)

    @property
    def has_solid_body(self):
        """True when the file carries a closed body, solid or surface model."""
        return bool(self.solid_count or self.closed_shell_count)

    @property
    def label(self):
        """Best available name for this part or component."""
        return self.name or self.product_name or self.file_name or 'Component'

    @property
    def is_assembly(self):
        return self.assembly_instance_count > 1

    @property
    def part_count(self):
        """Number of component instances, or 1 for a single solid part."""
        if self.assembly_instance_count:
            return self.assembly_instance_count
        if self.solid_count:
            return self.solid_count
        # A shelled part exports as a surface model with a closed shell,
        # which is still one body.
        if self.closed_shell_count:
            return self.closed_shell_count
        return None

    @property
    def draft_angles(self):
        """Distinct conical half-angles in degrees, rounded to 0.1."""
        return sorted({round(a, 1) for a in self.draft_angles_deg})

    @property
    def has_measurable_geometry(self):
        return self.bbox_min is not None or self.volume_mm3 is not None

    def estimated_mass_g(self, density_g_cm3=7.85):
        """Mass estimate in grams.

        Uses true volume when the file is a mesh; otherwise returns ``None``.
        A bounding-box volume is deliberately NOT used as a mass proxy - it
        would overstate mass for anything that is not a solid block.
        """
        if self.volume_mm3 is None:
            return None
        return (self.volume_mm3 / 1000.0) * density_g_cm3

    def bbox_volume_mm3(self):
        dims = self.dimensions
        if not dims:
            return None
        return dims[0] * dims[1] * dims[2]

    def summary_lines(self):
        """Human-readable list of what was actually measured."""
        lines = ["File:            %s" % self.file_name,
                 "Format:          %s" % self.file_format]
        if self.product_name:
            lines.append("Product name:    %s" % self.product_name)
        if self.units:
            lines.append("Units in file:   %s" % self.units)

        dims = self.dimensions
        if dims:
            lines.append("Bounding box:    %.2f x %.2f x %.2f mm" % dims)
            lines.append("Envelope volume: %.1f mm3" % self.bbox_volume_mm3())
        if self.volume_mm3 is not None:
            lines.append("Solid volume:    %.1f mm3" % self.volume_mm3)
        if self.surface_area_mm2 is not None:
            lines.append("Surface area:    %.1f mm2" % self.surface_area_mm2)
        if self.is_watertight is not None:
            lines.append("Watertight mesh: %s" % ("yes" if self.is_watertight else "NO"))
        if self.triangle_count:
            lines.append("Triangles:       %d" % self.triangle_count)
        if self.face_count:
            lines.append("B-rep faces:     %d (planar: %d)" % (self.face_count, self.plane_count))
        if self.solid_count:
            lines.append("Solid bodies:    %d" % self.solid_count)
        if self.cylinder_radii:
            lines.append("Cylindrical:     %d faces; diameters %s mm "
                         "(holes, bosses or rounds)"
                         % (len(self.cylinder_radii),
                            ", ".join("%.2f" % d
                                      for d in self.cylindrical_diameters)))
        if self.min_wall_thickness_mm is not None:
            lines.append("Min wall thick.: %.2f mm  (ray cast, %d samples)"
                         % (self.min_wall_thickness_mm, self.wall_thickness_rays))
        if self.draft_angles_deg:
            lines.append("Conical angles:  %s deg  (draft and chamfer faces)" %
                         ", ".join("%.1f" % a for a in self.draft_angles))
        if self.assembly_instance_count:
            lines.append("Assembly:        %d component instance(s), %d distinct "
                         "product(s); placements %s"
                         % (self.assembly_instance_count,
                            self.distinct_product_count,
                            "applied" if self.components_placed
                            else "NOT resolved"))
        if self.torus_minor_radii:
            lines.append("Fillet radii:    %s mm" %
                         ", ".join("%.2f" % r for r in self.fillet_radii))
        if self.bspline_surface_count:
            lines.append("Freeform faces:  %d" % self.bspline_surface_count)
        if not self.has_measurable_geometry:
            lines.append("Geometry:        none measurable from this file")
        return lines

    def to_dict(self):
        return {
            'file_name': self.file_name,
            'file_format': self.file_format,
            'readable': self.readable,
            'read_notes': list(self.read_notes),
            'product_name': self.product_name,
            'units': self.units,
            'dimensions_mm': self.dimensions,
            'bbox_volume_mm3': self.bbox_volume_mm3(),
            'volume_mm3': self.volume_mm3,
            'surface_area_mm2': self.surface_area_mm2,
            'is_watertight': self.is_watertight,
            'triangle_count': self.triangle_count,
            'face_count': self.face_count,
            'plane_count': self.plane_count,
            'solid_count': self.solid_count,
            'cylindrical_diameters_mm': self.cylindrical_diameters,
            'min_wall_thickness_mm': self.min_wall_thickness_mm,
            'wall_thickness_rays': self.wall_thickness_rays,
            'cone_half_angles_deg': self.draft_angles,
            'wall_draft_angles_deg': self.wall_draft_angles(),
            'undrafted_wall_count': self.undrafted_wall_count(),
            'assembly_instance_count': self.assembly_instance_count,
            'components_placed': self.components_placed,
            'components': [
                {'name': component.label,
                 'dimensions_mm': component.dimensions,
                 'face_count': component.face_count,
                 'cylindrical_diameters_mm': component.cylindrical_diameters}
                for component in self.components],
            'distinct_product_count': self.distinct_product_count,
            'part_count': self.part_count,
            'fillet_radii_mm': self.fillet_radii,
            'cone_count': self.cone_count,
            'bspline_surface_count': self.bspline_surface_count,
            'has_measurable_geometry': self.has_measurable_geometry,
        }


# --------------------------------------------------------------------------
# STEP (ISO 10303-21) parsing
# --------------------------------------------------------------------------

# Splits a STEP data section on ';' while ignoring ';' inside quoted strings.
_STEP_SPLIT_RE = re.compile(r"'(?:[^']|'')*'|;")
_INSTANCE_RE = re.compile(r"\A#(\d+)\s*=\s*(.+)\Z", re.S)
_ENTITY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_NUM = r"[-+]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[EeDd][-+]?[0-9]+)?"
_POINT_RE = re.compile(r"\(\s*(%s)\s*,\s*(%s)\s*,\s*(%s)\s*\)" % (_NUM, _NUM, _NUM))
_RADIUS_1_RE = re.compile(r",\s*#\d+\s*,\s*(%s)" % _NUM)
_RADIUS_2_RE = re.compile(r",\s*#\d+\s*,\s*(%s)\s*,\s*(%s)" % (_NUM, _NUM))
_REF_RE = re.compile(r"#(\d+)")
_CONE_RE = re.compile(
    r"CONICAL_SURFACE\s*\(\s*'(?:[^']|'')*'\s*,\s*#\d+\s*,\s*(%s)\s*,\s*(%s)"
    % (_NUM, _NUM))
_QUOTED_RE = re.compile(r"'((?:[^']|'')*)'")


def _to_float(text):
    try:
        return float(text.replace('D', 'E').replace('d', 'e'))
    except (ValueError, AttributeError):
        return None


def _step_statements(data_text):
    """Yield each ``#id = ENTITY(...)`` statement of a STEP data section."""
    start = 0
    for match in _STEP_SPLIT_RE.finditer(data_text):
        if match.group(0) != ';':
            continue  # a quoted string - skip over it
        statement = data_text[start:match.start()].strip()
        start = match.end()
        if statement:
            yield statement


def _step_units(statement):
    """Return (label, scale_to_mm) if the statement defines the length unit."""
    if 'LENGTH_UNIT' not in statement:
        return None
    if 'CONVERSION_BASED_UNIT' in statement:
        name = _QUOTED_RE.search(statement)
        label = name.group(1).strip().upper() if name else 'INCH'
        if 'INCH' in label or 'IN' == label:
            return ('inch', 25.4)
        if 'FOOT' in label or 'FT' == label:
            return ('foot', 304.8)
        return (label.lower(), 1.0)
    if 'SI_UNIT' in statement:
        if '.MILLI.' in statement:
            return ('millimetre', 1.0)
        if '.CENTI.' in statement:
            return ('centimetre', 10.0)
        if '.METRE.' in statement:
            return ('metre', 1000.0)
    return None


def _step_angle_unit(statement):
    """Return the factor converting the file's plane angle unit to degrees."""
    if 'PLANE_ANGLE_UNIT' not in statement:
        return None
    if 'CONVERSION_BASED_UNIT' in statement:
        name = _QUOTED_RE.search(statement)
        label = name.group(1).strip().upper() if name else ''
        if 'DEGREE' in label:
            return 1.0
    if 'SI_UNIT' in statement:
        return 180.0 / math.pi  # radians
    return None


def read_step(path, geom):
    """Populate ``geom`` from a STEP file.  Returns ``geom``.

    For an assembly, each component is also measured separately into
    ``geom.components`` so that findings can name the component they came
    from rather than the assembly as a whole.
    """
    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        text = handle.read()

    header_end = text.find('ENDSEC;')
    header = text[:header_end] if header_end != -1 else text[:4000]

    schema = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']*)'", header)
    if schema:
        geom.schema = schema.group(1)

    data_start = text.find('DATA;')
    data_text = text[data_start + 5:] if data_start != -1 else ''
    if not data_text.strip():
        geom.read_notes.append(
            "STEP file has no DATA section - nothing to measure.")
        geom.readable = True
        return geom

    # A CARTESIAN_POINT may be a model vertex, or merely the origin of a
    # surface's axis placement - and a placement origin can sit well outside
    # the solid. Only VERTEX_POINTs bound the part, so collect those first.
    vertex_refs = set()
    for statement in _step_statements(data_text):
        if 'VERTEX_POINT' not in statement:
            continue
        refs = _REF_RE.findall(statement)
        # #id = VERTEX_POINT('', #point)
        if len(refs) >= 2:
            vertex_refs.add(refs[-1])

    # An assembly stores each component in its own coordinate system, so the
    # placements have to be applied before anything is measured.
    from .step_assembly import read_step_assembly
    placement = read_step_assembly(path, _step_statements(data_text))

    # targets[0] is the whole model; the rest are its components. Every
    # measurement is tallied into the model and into the component it
    # belongs to.
    targets = [geom]
    rep_index = {}
    for rep_id in placement.component_reps:
        component = CADGeometry(file_path=geom.file_path,
                                file_name=geom.file_name,
                                file_format=geom.file_format)
        component.name = placement.name_of(
            rep_id, 'Component %d' % (len(targets)))
        component.product_name = component.name
        component.readable = True
        rep_index[rep_id] = len(targets)
        targets.append(component)

    bounds = [[[float('inf')] * 3, [float('-inf')] * 3] for _ in targets]
    unit_scale = None
    unit_label = None
    angle_to_degrees = None
    product_ids = set()
    # Reference tables, so a face can be resolved to its surface normal.
    directions = {}
    placements = {}
    plane_placement = {}
    face_surfaces = []

    for statement in _step_statements(data_text):
        instance = _INSTANCE_RE.match(statement)
        body = instance.group(2) if instance else statement
        entity_id = instance.group(1) if instance else None

        if unit_scale is None:
            unit = _step_units(body)
            if unit:
                unit_label, unit_scale = unit
        if angle_to_degrees is None:
            angle_to_degrees = _step_angle_unit(body)

        # Entity names present in this statement (a complex instance such as
        # "( LENGTH_UNIT() SI_UNIT(...) )" carries several).
        names = set(_ENTITY_RE.findall(body))

        # Which targets this entity counts towards.
        indices = [0]
        if entity_id is not None:
            owner = rep_index.get(placement.rep_of(entity_id))
            if owner is not None:
                indices.append(owner)

        if 'CARTESIAN_POINT' in names:
            point = _POINT_RE.search(body)
            if point:
                coords = [_to_float(point.group(i)) for i in (1, 2, 3)]
                if all(c is not None for c in coords):
                    for index in indices:
                        targets[index].point_count += 1
                    # Bound the part by its vertices only, unless the file
                    # defines none (then fall back to every point).
                    if not vertex_refs or entity_id in vertex_refs:
                        located = placement.place(entity_id, tuple(coords))
                        for index in indices:
                            low, high = bounds[index]
                            for axis in range(3):
                                low[axis] = min(low[axis], located[axis])
                                high[axis] = max(high[axis], located[axis])

        if entity_id and 'DIRECTION' in names:
            point = _POINT_RE.search(body)
            if point:
                vector = [_to_float(point.group(i)) for i in (1, 2, 3)]
                if all(v is not None for v in vector):
                    directions[entity_id] = tuple(vector)
        if entity_id and 'AXIS2_PLACEMENT_3D' in names:
            refs = _REF_RE.findall(body)
            # name, location, axis, ref_direction - the axis is the normal.
            if len(refs) >= 2:
                placements[entity_id] = refs[1]
        if entity_id and 'PLANE' in names:
            refs = _REF_RE.findall(body)
            if refs:
                plane_placement[entity_id] = refs[0]
        if 'ADVANCED_FACE' in names:
            refs = _REF_RE.findall(body)
            if refs:
                # name, (bounds...), face_geometry, same_sense - the surface
                # is the last reference in the argument list.
                face_surfaces.append((refs[-1], tuple(indices)))

        if 'CYLINDRICAL_SURFACE' in names:
            radius = _RADIUS_1_RE.search(body)
            if radius:
                value = _to_float(radius.group(1))
                if value is not None:
                    for index in indices:
                        targets[index].cylinder_radii.append(value)
        if 'TOROIDAL_SURFACE' in names:
            radii = _RADIUS_2_RE.search(body)
            if radii:
                minor = _to_float(radii.group(2))
                if minor is not None:
                    for index in indices:
                        targets[index].torus_minor_radii.append(abs(minor))
        if 'CONICAL_SURFACE' in names:
            cone = _CONE_RE.search(body)
            angle = _to_float(cone.group(2)) if cone else None
            for index in indices:
                targets[index].cone_count += 1
                if angle is not None:
                    # Stored raw here; converted to degrees once the file's
                    # plane angle unit is known.
                    targets[index].draft_angles_deg.append(angle)
        if 'SPHERICAL_SURFACE' in names:
            for index in indices:
                targets[index].sphere_count += 1
        if 'B_SPLINE_SURFACE' in names or 'BOUNDED_SURFACE' in names:
            for index in indices:
                targets[index].bspline_surface_count += 1
        if 'PLANE' in names:
            for index in indices:
                targets[index].plane_count += 1
        if 'ADVANCED_FACE' in names or 'FACE_SURFACE' in names:
            for index in indices:
                targets[index].face_count += 1
        if 'CLOSED_SHELL' in names or 'OPEN_SHELL' in names:
            for index in indices:
                targets[index].shell_count += 1
        if 'CLOSED_SHELL' in names:
            for index in indices:
                targets[index].closed_shell_count += 1
        if ('MANIFOLD_SOLID_BREP' in names
                or 'BREP_WITH_VOIDS' in names
                or 'FACETED_BREP' in names):
            for index in indices:
                targets[index].solid_count += 1
        if 'NEXT_ASSEMBLY_USAGE_OCCURRENCE' in names:
            geom.assembly_instance_count += 1
        if 'PRODUCT' in names:
            if instance:
                product_ids.add(instance.group(1))
            if geom.product_name is None:
                name = _QUOTED_RE.search(body)
                if name:
                    geom.product_name = name.group(1).strip() or None

    scale = unit_scale if unit_scale else 1.0
    factor = angle_to_degrees if angle_to_degrees else 180.0 / math.pi

    for index, target in enumerate(targets):
        target.units = unit_label or 'millimetre (assumed - no unit in file)'
        target.unit_scale_mm = scale
        low, high = bounds[index]
        if low[0] != float('inf'):
            target.bbox_min = tuple(round(v * scale, 6) for v in low)
            target.bbox_max = tuple(round(v * scale, 6) for v in high)
        if scale != 1.0:
            target.cylinder_radii = [r * scale for r in target.cylinder_radii]
            target.torus_minor_radii = [r * scale
                                        for r in target.torus_minor_radii]
        # Cone half-angles are stored in the file's plane angle unit, which
        # is radians unless the file says otherwise.
        target.draft_angles_deg = [abs(a) * factor
                                   for a in target.draft_angles_deg]

    geom.distinct_product_count = len(product_ids)

    # Resolve each face to its surface normal, so draft can be measured.
    # Only surfaces actually used by a face are considered.
    for surface_id, indices in face_surfaces:
        placement_id = plane_placement.get(surface_id)
        if placement_id is None:
            continue
        normal = directions.get(placements.get(placement_id))
        if normal:
            for index in indices:
                targets[index].plane_normals.append(normal)

    geom.readable = True
    geom.components_placed = bool(placement.component_reps)
    geom.components = targets[1:]
    if geom.assembly_instance_count > 1 and not geom.components_placed:
        geom.read_notes.append(
            "This is an assembly of %d components, but no placement "
            "transforms could be read from the file, so the bounding box is "
            "the union of the component geometry as defined and understates "
            "the installed envelope." % geom.assembly_instance_count)
    if not geom.face_count and not geom.solid_count:
        geom.read_notes.append(
            "No B-rep faces or solids found - this STEP file carries no solid "
            "model, so manufacturability checks that need geometry are skipped.")
    return geom


# --------------------------------------------------------------------------
# STL parsing
# --------------------------------------------------------------------------

def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _ray_triangle(origin, direction, v0, v1, v2, epsilon=1e-9):
    """Moller-Trumbore. Returns the distance along the ray, or None."""
    edge1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
    edge2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
    pvec = _cross(direction, edge2)
    det = _dot(edge1, pvec)
    if -epsilon < det < epsilon:
        return None
    inv_det = 1.0 / det
    tvec = (origin[0] - v0[0], origin[1] - v0[1], origin[2] - v0[2])
    u = _dot(tvec, pvec) * inv_det
    if u < 0.0 or u > 1.0:
        return None
    qvec = _cross(tvec, edge1)
    v = _dot(direction, qvec) * inv_det
    if v < 0.0 or u + v > 1.0:
        return None
    distance = _dot(edge2, qvec) * inv_det
    return distance if distance > epsilon else None


def ray_budget(triangle_count, work_limit=600000):
    """How many rays to cast, given the cost is rays x triangles.

    Dense meshes get fewer rays so a measurement still finishes in seconds.
    The report always states how many rays were actually cast.
    """
    if triangle_count <= 0:
        return 0
    return max(24, min(250, work_limit // max(1, triangle_count)))


def measure_wall_thickness(triangles, max_rays=None, progress=None):
    """Measure local wall thickness by casting rays into the solid.

    From the centre of a sample of faces, a ray is fired along the inward
    normal and the distance to the first face it meets is the local wall
    thickness there.

    This samples faces rather than testing all of them, so the result is the
    thinnest wall *found*, not a proven global minimum. Returns
    (thickness_mm, rays_cast) or (None, 0).
    """
    count = len(triangles)
    if count < 4:
        return (None, 0)

    if max_rays is None:
        max_rays = ray_budget(count)
    if max_rays <= 0:
        return (None, 0)

    step = max(1, count // max_rays)
    planned = max(1, len(range(0, count, step)))
    thinnest = None
    rays = 0

    for index in range(0, count, step):
        v0, v1, v2 = triangles[index]
        edge1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        edge2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        normal = _cross(edge1, edge2)
        length = math.sqrt(_dot(normal, normal))
        if length == 0:
            continue
        normal = (normal[0] / length, normal[1] / length, normal[2] / length)
        inward = (-normal[0], -normal[1], -normal[2])
        centroid = ((v0[0] + v1[0] + v2[0]) / 3.0,
                    (v0[1] + v1[1] + v2[1]) / 3.0,
                    (v0[2] + v1[2] + v2[2]) / 3.0)
        # Start just inside the surface so the source face is not hit.
        origin = (centroid[0] + inward[0] * 1e-6,
                  centroid[1] + inward[1] * 1e-6,
                  centroid[2] + inward[2] * 1e-6)

        rays += 1
        if progress and rays % 10 == 0:
            progress(rays / float(planned),
                     'Measuring wall thickness (%d of %d rays)'
                     % (rays, planned))
        nearest = None
        for other in range(count):
            if other == index:
                continue
            w0, w1, w2 = triangles[other]
            distance = _ray_triangle(origin, inward, w0, w1, w2)
            if distance is not None and (nearest is None or distance < nearest):
                nearest = distance
        if nearest is not None and (thinnest is None or nearest < thinnest):
            thinnest = nearest

    return (thinnest, rays)


def _stl_is_binary(path):
    size = os.path.getsize(path)
    with open(path, 'rb') as handle:
        head = handle.read(84)
    if len(head) < 84:
        return False
    count = struct.unpack('<I', head[80:84])[0]
    if size == 84 + count * 50:
        return True
    return not head[:5].lower().startswith(b'solid')


def _stl_triangles(path):
    """Yield (v0, v1, v2) vertex tuples from an STL file."""
    if _stl_is_binary(path):
        with open(path, 'rb') as handle:
            handle.seek(80)
            count = struct.unpack('<I', handle.read(4))[0]
            payload = handle.read(count * 50)
        for index in range(len(payload) // 50):
            chunk = payload[index * 50:index * 50 + 48]
            values = struct.unpack('<12f', chunk)
            yield (values[3:6], values[6:9], values[9:12])
    else:
        vertices = []
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            for line in handle:
                line = line.strip()
                if not line.startswith('vertex'):
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                vertices.append(tuple(float(p) for p in parts[1:4]))
                if len(vertices) == 3:
                    yield tuple(vertices)
                    vertices = []


def read_stl(path, geom, progress=None):
    """Populate ``geom`` from an STL mesh.  Returns ``geom``."""
    lo = [float('inf')] * 3
    hi = [float('-inf')] * 3
    volume6 = 0.0
    area2 = 0.0
    count = 0
    edges = {}

    triangles = []
    for v0, v1, v2 in _stl_triangles(path):
        count += 1
        triangles.append((v0, v1, v2))
        for vertex in (v0, v1, v2):
            for axis in range(3):
                lo[axis] = min(lo[axis], vertex[axis])
                hi[axis] = max(hi[axis], vertex[axis])

        # Signed volume of the tetrahedron (origin, v0, v1, v2), x6.
        cross = (v1[1] * v2[2] - v1[2] * v2[1],
                 v1[2] * v2[0] - v1[0] * v2[2],
                 v1[0] * v2[1] - v1[1] * v2[0])
        volume6 += v0[0] * cross[0] + v0[1] * cross[1] + v0[2] * cross[2]

        # Twice the triangle area = |(v1-v0) x (v2-v0)|
        a = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        b = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        n = (a[1] * b[2] - a[2] * b[1],
             a[2] * b[0] - a[0] * b[2],
             a[0] * b[1] - a[1] * b[0])
        area2 += (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5

        keys = [tuple(round(c, 5) for c in v) for v in (v0, v1, v2)]
        for i in range(3):
            edge = tuple(sorted((keys[i], keys[(i + 1) % 3])))
            edges[edge] = edges.get(edge, 0) + 1

    geom.triangle_count = count
    geom.readable = True
    if count == 0:
        geom.read_notes.append("STL file contains no triangles.")
        return geom

    geom.bbox_min = tuple(round(v, 6) for v in lo)
    geom.bbox_max = tuple(round(v, 6) for v in hi)
    geom.volume_mm3 = abs(volume6) / 6.0
    geom.surface_area_mm2 = area2 / 2.0
    geom.is_watertight = all(n == 2 for n in edges.values())
    geom.units = 'millimetre (assumed - STL carries no units)'
    geom.triangles = triangles
    if geom.is_watertight:
        # Thickness is only meaningful when the mesh is closed.
        thickness, rays = measure_wall_thickness(triangles, progress=progress)
        geom.min_wall_thickness_mm = thickness
        geom.wall_thickness_rays = rays

    if not geom.is_watertight:
        open_edges = sum(1 for n in edges.values() if n != 2)
        geom.read_notes.append(
            "Mesh is not watertight (%d edges are not shared by exactly two "
            "triangles); the volume figure is unreliable." % open_edges)
    return geom


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def read_cad(path, progress=None):
    """Read whatever geometry can be extracted from ``path``.

    Always returns a :class:`CADGeometry`.  Unreadable or unsupported files
    come back with ``readable=False`` and an explanation in ``read_notes``;
    they never raise.
    """
    geom = CADGeometry(file_path=str(path), file_name=os.path.basename(str(path)))
    extension = os.path.splitext(str(path))[1].lower()
    geom.file_format = RECOGNISED_EXTENSIONS.get(extension, 'UNKNOWN')

    if not os.path.exists(path):
        geom.read_notes.append("File not found: %s" % path)
        return geom

    if extension not in READABLE_EXTENSIONS:
        if extension in RECOGNISED_EXTENSIONS:
            geom.read_notes.append(
                "%s files are a closed vendor format and cannot be measured "
                "without that vendor's software. Export the model as STEP "
                "(AP203/AP214) or STL and analyse that file instead."
                % geom.file_format)
        else:
            geom.read_notes.append(
                "Unrecognised file extension '%s'." % extension)
        return geom

    try:
        if extension == '.stl':
            return read_stl(path, geom, progress=progress)
        return read_step(path, geom)
    except (OSError, ValueError, struct.error) as error:
        geom.readable = False
        geom.read_notes.append("Could not read file: %s" % error)
        return geom

# --------------------------------------------------------------------------
# STEP edge extraction, for wireframe views
# --------------------------------------------------------------------------

_EDGE_CURVE_RE = re.compile(
    r"EDGE_CURVE\s*\(\s*'(?:[^']|'')*'\s*,\s*#(\d+)\s*,\s*#(\d+)\s*,"
    r"\s*#(\d+)\s*,\s*\.([TF])\.", re.S)

# Reading edges means holding the point table in memory, so cap the file size.
MAX_EDGE_FILE_BYTES = 25 * 1024 * 1024
ARC_SEGMENTS = 48


def _arc_points(centre, axis, ref, radius, start_angle, sweep, segments):
    """Sample an arc lying in the plane defined by ``axis`` and ``ref``."""
    z = _normalise_vec(axis) or (0.0, 0.0, 1.0)
    x = _normalise_vec(ref)
    if x is None:
        x = (1.0, 0.0, 0.0)
    # Re-orthogonalise x against z, then y completes the right-handed frame.
    dot = sum(a * b for a, b in zip(x, z))
    x = _normalise_vec(tuple(x[i] - dot * z[i] for i in range(3))) or (1.0, 0.0, 0.0)
    y = (z[1] * x[2] - z[2] * x[1],
         z[2] * x[0] - z[0] * x[2],
         z[0] * x[1] - z[1] * x[0])

    points = []
    for step in range(segments + 1):
        angle = start_angle + sweep * (step / float(segments))
        cos_a, sin_a = math.cos(angle) * radius, math.sin(angle) * radius
        points.append(tuple(centre[i] + x[i] * cos_a + y[i] * sin_a
                            for i in range(3)))
    return points


def _normalise_vec(vector):
    if not vector:
        return None
    length = math.sqrt(sum(component ** 2 for component in vector))
    if length == 0:
        return None
    return tuple(component / length for component in vector)


def read_step_edges(path, max_bytes=MAX_EDGE_FILE_BYTES):
    """Return the model's edges as polylines in millimetres.

    Straight edges become two-point lines; circular edges are swept properly
    using the curve's own centre, axis and sense flag, so holes and fillets
    draw as arcs rather than chords. Curve types that are not lines or
    circles fall back to a straight chord between the edge's vertices.

    Returns an empty list when the file is missing, too large to hold in
    memory, or carries no edges. It never raises.
    """
    from .step_assembly import apply, is_identity, read_step_assembly

    try:
        if os.path.getsize(path) > max_bytes:
            return []
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            text = handle.read()
    except OSError:
        return []

    start = text.find('DATA;')
    if start == -1:
        return []
    data_text = text[start + 5:]

    placement = read_step_assembly(path, _step_statements(data_text))

    points = {}
    vertices = {}
    directions = {}
    placements = {}
    circles = {}
    # An EDGE_CURVE points at a SURFACE_CURVE or SEAM_CURVE, whose first
    # reference is the actual 3D basis curve. Follow that hop.
    basis_curves = {}
    edges = []
    scale = None

    for statement in _step_statements(data_text):
        instance = _INSTANCE_RE.match(statement)
        body = instance.group(2) if instance else statement
        entity_id = instance.group(1) if instance else None
        names = set(_ENTITY_RE.findall(body))

        if scale is None:
            unit = _step_units(body)
            if unit:
                scale = unit[1]

        if entity_id and 'CARTESIAN_POINT' in names:
            found = _POINT_RE.search(body)
            if found:
                coords = [_to_float(found.group(i)) for i in (1, 2, 3)]
                if all(c is not None for c in coords):
                    points[entity_id] = tuple(coords)
        elif entity_id and 'DIRECTION' in names:
            found = _POINT_RE.search(body)
            if found:
                coords = [_to_float(found.group(i)) for i in (1, 2, 3)]
                if all(c is not None for c in coords):
                    directions[entity_id] = tuple(coords)
        elif entity_id and 'VERTEX_POINT' in names:
            refs = _REF_RE.findall(body)
            if refs:
                vertices[entity_id] = refs[-1]
        elif entity_id and 'AXIS2_PLACEMENT_3D' in names:
            refs = _REF_RE.findall(body)
            if len(refs) >= 3:
                placements[entity_id] = (refs[0], refs[1], refs[2])
            elif len(refs) == 2:
                placements[entity_id] = (refs[0], refs[1], None)
        elif entity_id and 'CIRCLE' in names:
            refs = _REF_RE.findall(body)
            radius = _RADIUS_1_RE.search(body)
            if refs and radius:
                value = _to_float(radius.group(1))
                if value is not None:
                    circles[entity_id] = (refs[0], value)
        elif entity_id and ('SURFACE_CURVE' in names or 'SEAM_CURVE' in names):
            refs = _REF_RE.findall(body)
            if refs:
                basis_curves[entity_id] = refs[0]

        if 'EDGE_CURVE' in names:
            found = _EDGE_CURVE_RE.search(body)
            if found:
                edges.append((found.group(1), found.group(2),
                              found.group(3), found.group(4) == 'T'))

    factor = scale if scale else 1.0
    polylines = []

    def locate(point_id, point):
        """Move a point into assembly coordinates."""
        return placement.place(point_id, point) if point_id else point

    for start_vertex, end_vertex, curve_id, same_sense in edges:
        start_id = vertices.get(start_vertex)
        end_id = vertices.get(end_vertex)
        start_point = points.get(start_id)
        end_point = points.get(end_id)
        if start_point is None or end_point is None:
            continue
        component = placement.transform_for_point(start_id)

        def emit(line):
            """Record a polyline, placed into assembly coordinates."""
            if component is None or is_identity(component):
                polylines.append(line)
            else:
                polylines.append([apply(component, point) for point in line])

        circle = circles.get(_resolve_curve(curve_id, basis_curves, circles))
        if circle is None:
            emit([start_point, end_point])
            continue

        axis_id, radius = circle
        axis_entry = placements.get(axis_id)
        if not axis_entry:
            emit([start_point, end_point])
            continue
        centre = points.get(axis_entry[0])
        axis = directions.get(axis_entry[1])
        ref = directions.get(axis_entry[2]) if axis_entry[2] else None
        if centre is None or axis is None:
            emit([start_point, end_point])
            continue

        arc = _circle_arc(centre, axis, ref, radius,
                          start_point, end_point, same_sense)
        emit(arc if arc else [start_point, end_point])

    if factor != 1.0:
        polylines = [[tuple(c * factor for c in point) for point in line]
                     for line in polylines]
    return polylines


def _resolve_curve(curve_id, basis_curves, circles, max_hops=4):
    """Follow SURFACE_CURVE / SEAM_CURVE indirection to the basis curve."""
    seen = set()
    current = curve_id
    for _ in range(max_hops):
        if current in circles or current not in basis_curves:
            return current
        if current in seen:
            return current
        seen.add(current)
        current = basis_curves[current]
    return current


def _circle_arc(centre, axis, ref, radius, start_point, end_point, same_sense):
    """Sweep a circular edge between its two vertices, or None."""
    z = _normalise_vec(axis)
    if z is None:
        return None
    x = _normalise_vec(ref) if ref else None
    if x is None:
        # Any vector perpendicular to the axis will do as the reference.
        seed = (1.0, 0.0, 0.0) if abs(z[0]) < 0.9 else (0.0, 1.0, 0.0)
        dot = sum(a * b for a, b in zip(seed, z))
        x = _normalise_vec(tuple(seed[i] - dot * z[i] for i in range(3)))
        if x is None:
            return None
    dot = sum(a * b for a, b in zip(x, z))
    x = _normalise_vec(tuple(x[i] - dot * z[i] for i in range(3)))
    if x is None:
        return None
    y = (z[1] * x[2] - z[2] * x[1],
         z[2] * x[0] - z[0] * x[2],
         z[0] * x[1] - z[1] * x[0])

    def angle_of(point):
        local = tuple(point[i] - centre[i] for i in range(3))
        return math.atan2(sum(a * b for a, b in zip(local, y)),
                          sum(a * b for a, b in zip(local, x)))

    start_angle = angle_of(start_point)
    end_angle = angle_of(end_point)

    two_pi = 2.0 * math.pi
    if same_sense:
        sweep = (end_angle - start_angle) % two_pi
    else:
        sweep = -((start_angle - end_angle) % two_pi)
    if abs(sweep) < 1e-9:
        sweep = two_pi if same_sense else -two_pi

    segments = max(6, int(ARC_SEGMENTS * abs(sweep) / two_pi))
    return _arc_points(centre, z, x, radius, start_angle, sweep, segments)
