"""Tests for the SVG view renderer."""

import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dfx_analyzers.cad_reader import read_cad, read_step_edges
from dfx_analyzers.render import (DEFAULT_VIEWS, render_mesh_view,
                                  render_note, render_views,
                                  render_wireframe_view)
from test_cad_reader import cube_stl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'example_parts')
BRACKET_STEP = os.path.join(PARTS, 'sample_bracket.STEP')
BRACKET_STL = os.path.join(PARTS, 'sample_bracket.stl')


def parse(svg):
    """Parse the SVG, which also proves it is well-formed XML."""
    return ET.fromstring(svg)


class TestMeshViews(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.geom = read_cad(BRACKET_STL)

    def test_every_default_view_renders_shaded(self):
        views = render_views(self.geom)
        self.assertEqual([v['name'] for v in views], list(DEFAULT_VIEWS))
        for view in views:
            self.assertEqual(view['kind'], 'shaded')
            parse(view['svg'])

    def test_back_faces_are_culled(self):
        """A closed cube shows at most half its faces from any direction."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'cube.stl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(cube_stl(10.0))
            geom = read_cad(path)
        svg = render_mesh_view(geom.triangles, (0.0, 0.0, -1.0), label='Top')
        root = parse(svg)
        polygons = [e for e in root.iter() if e.tag.endswith('polygon')]
        self.assertGreater(len(polygons), 0)
        self.assertLessEqual(len(polygons), 6)  # 12 triangles, half face away

    def test_empty_mesh_renders_nothing(self):
        self.assertIsNone(render_mesh_view([], (0.0, 0.0, 1.0)))

    def test_degenerate_direction_is_rejected(self):
        self.assertIsNone(render_mesh_view(self.geom.triangles, (0.0, 0.0, 0.0)))


class TestWireframeViews(unittest.TestCase):

    def test_step_file_renders_wireframe(self):
        geom = read_cad(BRACKET_STEP)
        edges = read_step_edges(BRACKET_STEP)
        self.assertTrue(edges)
        views = render_views(geom, edges=edges)
        self.assertEqual(len(views), len(DEFAULT_VIEWS))
        for view in views:
            self.assertEqual(view['kind'], 'wireframe')
            parse(view['svg'])

    def test_circular_edges_are_swept_not_chorded(self):
        """A hole must come through as an arc, not a two-point chord."""
        edges = read_step_edges(BRACKET_STEP)
        arcs = [line for line in edges if len(line) > 2]
        self.assertGreater(len(arcs), 0, 'no circular edges were swept')

    def test_no_edges_renders_nothing(self):
        self.assertIsNone(render_wireframe_view([], (1.0, 1.0, 1.0)))

    def test_single_point_lines_are_ignored(self):
        self.assertIsNone(render_wireframe_view([[(0.0, 0.0, 0.0)]],
                                                (1.0, 1.0, 1.0)))


class TestRenderNotes(unittest.TestCase):

    def test_unreadable_file_explains_why_there_are_no_views(self):
        geom = read_cad('/no/such/file.step')
        self.assertEqual(render_views(geom), [])
        self.assertIn('could not be read', render_note(geom))

    def test_note_is_none_when_views_exist(self):
        geom = read_cad(BRACKET_STL)
        self.assertIsNone(render_note(geom))

    def test_edges_are_not_read_from_an_oversized_file(self):
        self.assertEqual(read_step_edges(BRACKET_STEP, max_bytes=10), [])

    def test_missing_file_gives_no_edges(self):
        self.assertEqual(read_step_edges('/no/such/file.step'), [])


class TestReportEmbedsViews(unittest.TestCase):

    def test_html_report_contains_the_views(self):
        from dfx_analyzers import ComprehensiveDFXAnalyzer
        analyzer = ComprehensiveDFXAnalyzer(BRACKET_STEP)
        html = analyzer.to_html({})
        self.assertIn('<svg', html)
        self.assertIn('Views', html)

    def test_views_can_be_switched_off(self):
        from dfx_analyzers import ComprehensiveDFXAnalyzer
        analyzer = ComprehensiveDFXAnalyzer(BRACKET_STEP)
        html = analyzer.to_html({}, include_views=False)
        self.assertNotIn('<svg', html)


if __name__ == '__main__':
    unittest.main()
