"""Assembly placement for STEP files.

A STEP assembly stores each component's geometry in its own coordinate
system, and records separately where that component sits in the assembly.
Reading the geometry without applying those placements piles every component
on the origin: a two-part assembly whose cover sits on top of its plate
reported an 8 mm stack as 5 mm, and drew the two parts overlapping.

This module reads the placement chain

    CONTEXT_DEPENDENT_SHAPE_REPRESENTATION
      -> REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION
        -> ITEM_DEFINED_TRANSFORMATION(source_axis, target_axis)

and works out, for every CARTESIAN_POINT, which component it belongs to and
where that component sits. Standard library only.
"""

import math
import os
import re

# Holding the reference graph costs memory, so cap the file size.
MAX_ASSEMBLY_FILE_BYTES = 25 * 1024 * 1024

IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
ORIGIN = (0.0, 0.0, 0.0)

_SHAPE_REP_NAMES = (
    'SHAPE_REPRESENTATION',
    'ADVANCED_BREP_SHAPE_REPRESENTATION',
    'MANIFOLD_SURFACE_SHAPE_REPRESENTATION',
    'GEOMETRICALLY_BOUNDED_SURFACE_SHAPE_REPRESENTATION',
    'FACETED_BREP_SHAPE_REPRESENTATION',
)

_ITEM_TRANSFORM_RE = re.compile(
    r"ITEM_DEFINED_TRANSFORMATION\s*\(\s*'(?:[^']|'')*'\s*,\s*"
    r"'(?:[^']|'')*'\s*,\s*#(\d+)\s*,\s*#(\d+)")


# --------------------------------------------------------------------------
# Small rigid-transform helpers. A transform is (rotation, translation),
# where rotation is three rows.
# --------------------------------------------------------------------------

def _normalise(vector):
    length = math.sqrt(sum(component ** 2 for component in vector))
    if length == 0:
        return None
    return tuple(component / length for component in vector)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def axis_frame(origin, axis, ref):
    """Rigid transform taking local coordinates into the frame's parent."""
    z = _normalise(axis) or (0.0, 0.0, 1.0)
    x = _normalise(ref) if ref else None
    if x is None:
        seed = (1.0, 0.0, 0.0) if abs(z[0]) < 0.9 else (0.0, 1.0, 0.0)
        x = seed
    projection = _dot(x, z)
    x = _normalise(tuple(x[i] - projection * z[i] for i in range(3)))
    if x is None:
        x = (1.0, 0.0, 0.0)
    y = _cross(z, x)
    # Columns of the rotation are the frame's axes, so rows are as below.
    rotation = ((x[0], y[0], z[0]),
                (x[1], y[1], z[1]),
                (x[2], y[2], z[2]))
    return (rotation, tuple(origin))


def apply(transform, point):
    rotation, translation = transform
    return tuple(_dot(rotation[i], point) + translation[i] for i in range(3))


def compose(outer, inner):
    """The transform equivalent to applying ``inner`` then ``outer``."""
    rotation_a, translation_a = outer
    rotation_b, translation_b = inner
    rotation = tuple(
        tuple(sum(rotation_a[i][k] * rotation_b[k][j] for k in range(3))
              for j in range(3))
        for i in range(3))
    translation = tuple(
        _dot(rotation_a[i], translation_b) + translation_a[i] for i in range(3))
    return (rotation, translation)


def invert(transform):
    rotation, translation = transform
    transposed = tuple(tuple(rotation[j][i] for j in range(3)) for i in range(3))
    moved = tuple(-_dot(transposed[i], translation) for i in range(3))
    return (transposed, moved)


def is_identity(transform, tolerance=1e-9):
    rotation, translation = transform
    for i in range(3):
        if abs(translation[i]) > tolerance:
            return False
        for j in range(3):
            expected = 1.0 if i == j else 0.0
            if abs(rotation[i][j] - expected) > tolerance:
                return False
    return True


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

class AssemblyPlacement:
    """Where each component sits, and which points belong to which."""

    def __init__(self):
        self.transforms = {}        # rep id -> world transform
        self.point_rep = {}         # cartesian point id -> rep id
        self.entity_rep = {}        # any geometry entity id -> rep id
        self.component_reps = []    # rep ids that are placed components
        self.names = {}             # rep id -> component product name

    @property
    def is_assembly(self):
        return len(self.component_reps) > 1

    def rep_of(self, entity_id):
        """Which component an entity belongs to, or None."""
        return self.entity_rep.get(entity_id)

    def name_of(self, rep_id, fallback=None):
        return self.names.get(rep_id) or fallback

    def transform_for_point(self, point_id):
        rep = self.point_rep.get(point_id)
        if rep is None:
            return None
        return self.transforms.get(rep)

    def place(self, point_id, point):
        """Move a point into assembly coordinates."""
        transform = self.transform_for_point(point_id)
        if transform is None or is_identity(transform):
            return point
        return apply(transform, point)


def read_step_assembly(path, statements, max_bytes=MAX_ASSEMBLY_FILE_BYTES):
    """Work out component placements from an iterable of STEP statements.

    ``statements`` is re-iterated, so pass a callable returning a fresh
    iterator, or a list. Returns an :class:`AssemblyPlacement`, empty when
    the file is a single part or too large to analyse.
    """
    placement = AssemblyPlacement()
    try:
        if path and os.path.getsize(path) > max_bytes:
            return placement
    except OSError:
        return placement

    from .cad_reader import (_ENTITY_RE, _INSTANCE_RE, _POINT_RE, _REF_RE,
                             _to_float)

    points = {}
    directions = {}
    placements = {}            # axis placement id -> (origin, axis, ref) ids
    reps = {}                  # rep id -> item ids
    product_names = {}         # product id -> name
    shape_definitions = []     # (product definition shape id, rep id)
    graph = {}                 # any id -> ids it references
    kinds = {}                 # id -> set of entity names
    relationships = []         # (child_rep, parent_rep, transform_id)
    transform_axes = {}        # transform id -> (source axis, target axis)

    for statement in statements:
        instance = _INSTANCE_RE.match(statement)
        if not instance:
            continue
        entity_id, body = instance.group(1), instance.group(2)
        names = set(_ENTITY_RE.findall(body))
        refs = _REF_RE.findall(body)
        graph[entity_id] = refs
        kinds[entity_id] = names

        if 'CARTESIAN_POINT' in names:
            found = _POINT_RE.search(body)
            if found:
                coords = [_to_float(found.group(i)) for i in (1, 2, 3)]
                if all(c is not None for c in coords):
                    points[entity_id] = tuple(coords)
        elif 'DIRECTION' in names:
            found = _POINT_RE.search(body)
            if found:
                coords = [_to_float(found.group(i)) for i in (1, 2, 3)]
                if all(c is not None for c in coords):
                    directions[entity_id] = tuple(coords)
        elif 'AXIS2_PLACEMENT_3D' in names:
            placements[entity_id] = (
                refs[0] if len(refs) > 0 else None,
                refs[1] if len(refs) > 1 else None,
                refs[2] if len(refs) > 2 else None)

        if names & set(_SHAPE_REP_NAMES):
            reps[entity_id] = refs
        if 'PRODUCT' in names:
            quoted = re.search(r"'((?:[^']|'')*)'", body)
            if quoted:
                product_names[entity_id] = quoted.group(1).strip()
        if 'SHAPE_DEFINITION_REPRESENTATION' in names and len(refs) >= 2:
            shape_definitions.append((refs[0], refs[1]))
        if 'ITEM_DEFINED_TRANSFORMATION' in names:
            found = _ITEM_TRANSFORM_RE.search(body)
            if found:
                transform_axes[entity_id] = (found.group(1), found.group(2))
        if 'REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION' in names:
            # ( REPRESENTATION_RELATIONSHIP('','',#child,#parent)
            #   REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#transform) )
            rep_refs = [r for r in refs if r in reps or r in transform_axes]
            if len(refs) >= 3:
                relationships.append((refs[0], refs[1], refs[2]))
            del rep_refs

    if not relationships or len(reps) < 2:
        return placement

    def frame(axis_id):
        entry = placements.get(axis_id)
        if not entry:
            return (IDENTITY, ORIGIN)
        origin = points.get(entry[0], ORIGIN)
        axis = directions.get(entry[1]) if entry[1] else None
        ref = directions.get(entry[2]) if entry[2] else None
        return axis_frame(origin, axis or (0.0, 0.0, 1.0), ref)

    # child rep -> (parent rep, transform child-space -> parent-space)
    parents = {}
    for child, parent, transform_id in relationships:
        if child not in reps or parent not in reps:
            continue
        axes = transform_axes.get(transform_id)
        if not axes:
            continue
        source = frame(axes[0])
        target = frame(axes[1])
        parents[child] = (parent, compose(target, invert(source)))

    def world_transform(rep_id, seen=None):
        seen = seen or set()
        if rep_id in seen or rep_id not in parents:
            return (IDENTITY, ORIGIN)
        seen.add(rep_id)
        parent, local = parents[rep_id]
        return compose(world_transform(parent, seen), local)

    for rep_id in reps:
        placement.transforms[rep_id] = world_transform(rep_id)
    placement.component_reps = sorted(parents)

    # Assign geometry to the component whose shape reaches it. Bare axis
    # placements are skipped: the identity placement is shared between the
    # root and its components, and would otherwise claim their geometry.
    for rep_id in placement.component_reps + [r for r in reps if r not in parents]:
        seeds = [item for item in reps.get(rep_id, ())
                 if 'AXIS2_PLACEMENT_3D' not in kinds.get(item, ())]
        stack = list(seeds)
        visited = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            placement.entity_rep.setdefault(current, rep_id)
            if current in points:
                placement.point_rep.setdefault(current, rep_id)
                continue
            stack.extend(graph.get(current, ()))

    # Name each component, by walking from its shape representation back to
    # the PRODUCT that defines it.
    for definition_id, rep_id in shape_definitions:
        if rep_id not in reps:
            continue
        stack = [definition_id]
        seen = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            if current in product_names:
                placement.names[rep_id] = product_names[current]
                break
            stack.extend(graph.get(current, ()))

    return placement
