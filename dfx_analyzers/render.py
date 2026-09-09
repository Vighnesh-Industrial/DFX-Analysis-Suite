"""Orthographic SVG views of a CAD model.

Standard library only, in line with the project's dependency policy: the
geometry is projected and shaded here rather than handed to a renderer.

Two kinds of picture are produced, depending on what the file can give us:

* **Shaded** views, from a mesh. Triangles are back-face culled, sorted by
  depth (painter's algorithm) and flat shaded.
* **Wireframe** views, from a STEP B-rep. Edges are drawn from the model's
  own edge curves, with circles and arcs swept properly rather than chorded.

Nothing here invents geometry: a view is only produced when the file supplies
the geometry to draw.
"""

import math
from html import escape

# Viewing direction for each named view, pointing from the camera toward the
# model, in model space.
VIEW_DIRECTIONS = {
    'iso': (-1.0, 1.0, -1.0),
    'front': (0.0, 1.0, 0.0),
    'top': (0.0, 0.0, -1.0),
    'right': (-1.0, 0.0, 0.0),
}

VIEW_LABELS = {
    'iso': 'Isometric',
    'front': 'Front (looking along +Y)',
    'top': 'Top (looking down -Z)',
    'right': 'Right (looking along -X)',
}

DEFAULT_VIEWS = ('iso', 'front', 'top', 'right')

# Above this a painter's-algorithm SVG becomes too large to be useful inline.
MAX_SHADED_TRIANGLES = 60000

FACE_RGB = (109, 132, 180)
EDGE_STROKE = '#2b3a55'


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


def _basis(direction):
    """Build a camera basis (right, up, forward) for a viewing direction."""
    forward = _normalise(direction)
    if forward is None:
        return None
    world_up = (0.0, 0.0, 1.0)
    if abs(_dot(forward, world_up)) > 0.999:
        world_up = (0.0, 1.0, 0.0)
    right = _normalise(_cross(forward, world_up))
    if right is None:
        return None
    up = _cross(right, forward)
    return right, up, forward


class _Projector:
    """Maps model points onto an SVG canvas, preserving aspect ratio."""

    def __init__(self, basis, points, width, height, margin):
        self.right, self.up, self.forward = basis
        self.width = width
        self.height = height

        flat = [(_dot(p, self.right), _dot(p, self.up)) for p in points]
        xs = [p[0] for p in flat]
        ys = [p[1] for p in flat]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)
        self.scale = min((width - 2 * margin) / span_x,
                         (height - 2 * margin) / span_y)
        self.offset_x = (width - (span_x * self.scale)) / 2.0 - min_x * self.scale
        self.offset_y = (height - (span_y * self.scale)) / 2.0 - min_y * self.scale

    def to_canvas(self, point):
        x = _dot(point, self.right) * self.scale + self.offset_x
        y = _dot(point, self.up) * self.scale + self.offset_y
        # SVG's y axis points down.
        return (x, self.height - y)

    def depth(self, point):
        return _dot(point, self.forward)


def _headlight(basis):
    """A light fixed to the camera, so every view is lit the same way.

    A light fixed in model space leaves whole views in shadow - the right
    hand view of a part came out almost black.
    """
    right, up, forward = basis
    direction = tuple(-forward[i] + 0.38 * right[i] + 0.55 * up[i]
                      for i in range(3))
    return _normalise(direction) or (0.0, 0.0, 1.0)


def _shade(normal, light):
    """Flat shading intensity for a face normal, 0.30 to 1.0."""
    unit = _normalise(normal)
    if unit is None:
        return 0.6
    lambertian = max(0.0, _dot(unit, light))
    return 0.30 + 0.70 * lambertian


def _fill(intensity):
    r, g, b = (min(255, int(channel * intensity + 26)) for channel in FACE_RGB)
    return '#%02x%02x%02x' % (r, g, b)


def _svg_open(width, height, label):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
        'width="%d" height="%d" role="img" aria-label="%s view">'
        '<rect width="%d" height="%d" fill="#f4f6fa"/>'
        % (width, height, width, height, escape(label), width, height))


def _svg_caption(label, width, height, detail=''):
    text = escape(label if not detail else '%s - %s' % (label, detail))
    return ('<text x="10" y="%d" font-family="system-ui,sans-serif" '
            'font-size="11" fill="#5a6a85">%s</text></svg>'
            % (height - 9, text))


def render_mesh_view(triangles, direction, width=380, height=290, margin=22,
                     label=''):
    """Shaded orthographic SVG of a triangle mesh, or None."""
    if not triangles:
        return None
    basis = _basis(direction)
    if basis is None:
        return None

    vertices = [v for triangle in triangles for v in triangle]
    projector = _Projector(basis, vertices, width, height, margin)
    forward = basis[2]
    light = _headlight(basis)

    drawable = []
    for v0, v1, v2 in triangles:
        edge1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        edge2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        normal = _cross(edge1, edge2)
        if _dot(normal, forward) >= 0:
            continue  # back face
        depth = (_dot(v0, forward) + _dot(v1, forward) + _dot(v2, forward)) / 3.0
        drawable.append((depth, (v0, v1, v2), normal))

    if not drawable:
        return None
    # Painter's algorithm: farthest first.
    drawable.sort(key=lambda item: -item[0])

    parts = [_svg_open(width, height, label)]
    for _, triangle, normal in drawable:
        points = ' '.join('%.1f,%.1f' % projector.to_canvas(v) for v in triangle)
        colour = _fill(_shade(normal, light))
        # Stroke the polygon in its own fill colour: adjacent SVG polygons
        # otherwise leave hairline seams that read as surface detail.
        parts.append('<polygon points="%s" fill="%s" stroke="%s" '
                     'stroke-width="0.8"/>' % (points, colour, colour))
    parts.append(_svg_caption(label, width, height, 'shaded'))
    return ''.join(parts)


def render_wireframe_view(polylines, direction, width=380, height=290,
                          margin=22, label=''):
    """Wireframe orthographic SVG from model edges, or None."""
    polylines = [line for line in polylines if len(line) >= 2]
    if not polylines:
        return None
    basis = _basis(direction)
    if basis is None:
        return None

    points = [point for line in polylines for point in line]
    projector = _Projector(basis, points, width, height, margin)

    parts = [_svg_open(width, height, label),
             '<g fill="none" stroke="%s" stroke-width="1" '
             'stroke-linecap="round" stroke-linejoin="round" '
             'opacity="0.85">' % EDGE_STROKE]
    for line in polylines:
        coordinates = ' '.join('%.2f,%.2f' % projector.to_canvas(p) for p in line)
        parts.append('<polyline points="%s"/>' % coordinates)
    parts.append('</g>')
    parts.append(_svg_caption(label, width, height, 'wireframe'))
    return ''.join(parts)


def render_views(geometry, edges=None, views=DEFAULT_VIEWS, width=380, height=290):
    """Render the named views of a model.

    Returns a list of ``{'name', 'label', 'kind', 'svg'}`` dicts. Views that
    cannot be drawn are left out rather than faked.
    """
    triangles = list(getattr(geometry, 'triangles', None) or ())
    use_mesh = bool(triangles) and len(triangles) <= MAX_SHADED_TRIANGLES

    rendered = []
    for name in views:
        direction = VIEW_DIRECTIONS.get(name)
        if direction is None:
            continue
        label = VIEW_LABELS.get(name, name.title())
        svg = None
        kind = None
        if use_mesh:
            svg = render_mesh_view(triangles, direction, width, height,
                                   label=label)
            kind = 'shaded'
        if svg is None and edges:
            svg = render_wireframe_view(edges, direction, width, height,
                                        label=label)
            kind = 'wireframe'
        if svg:
            rendered.append({'name': name, 'label': label, 'kind': kind,
                             'svg': svg})
    return rendered


def render_note(geometry, edges=None):
    """One line explaining why there are no views, or None when there are."""
    triangles = getattr(geometry, 'triangles', None) or ()
    if triangles and len(triangles) > MAX_SHADED_TRIANGLES:
        return ("The mesh has %d triangles, too many to draw inline. Supply a "
                "coarser export to see shaded views." % len(triangles))
    if not triangles and not edges:
        if not geometry.readable:
            return "No views: the file could not be read."
        return ("No views: this file carries no mesh and no B-rep edges to "
                "draw. Export STEP with solid geometry, or an STL.")
    return None
