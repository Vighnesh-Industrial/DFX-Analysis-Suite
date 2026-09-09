"""Tests for the CAD geometry reader."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers.cad_reader import read_cad

EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'example_parts')
SAMPLE_STEP = os.path.join(EXAMPLES, 'sample_bracket.STEP')
SAMPLE_STL = os.path.join(EXAMPLES, 'sample_bracket.stl')


def cube_stl(side):
    """An ASCII STL of a cube with the given side length, at the origin."""
    s = float(side)
    corners = {
        'zmin': [((0, 0, 0), (0, s, 0), (s, s, 0)), ((0, 0, 0), (s, s, 0), (s, 0, 0))],
        'zmax': [((0, 0, s), (s, s, s), (0, s, s)), ((0, 0, s), (s, 0, s), (s, s, s))],
        'ymin': [((0, 0, 0), (s, 0, 0), (s, 0, s)), ((0, 0, 0), (s, 0, s), (0, 0, s))],
        'ymax': [((0, s, 0), (0, s, s), (s, s, s)), ((0, s, 0), (s, s, s), (s, s, 0))],
        'xmin': [((0, 0, 0), (0, 0, s), (0, s, s)), ((0, 0, 0), (0, s, s), (0, s, 0))],
        'xmax': [((s, 0, 0), (s, s, 0), (s, s, s)), ((s, 0, 0), (s, s, s), (s, 0, s))],
    }
    lines = ['solid cube']
    for facets in corners.values():
        for triangle in facets:
            lines.append('facet normal 0 0 0')
            lines.append('  outer loop')
            for vertex in triangle:
                lines.append('    vertex %f %f %f' % vertex)
            lines.append('  endloop')
            lines.append('endfacet')
    lines.append('endsolid cube')
    return '\n'.join(lines)


class TestStepReader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.geom = read_cad(SAMPLE_STEP)

    def test_file_is_readable(self):
        self.assertTrue(self.geom.readable)
        self.assertEqual(self.geom.file_format, 'STEP')
        self.assertEqual(self.geom.read_notes, [])

    def test_product_name_and_units(self):
        self.assertEqual(self.geom.product_name, 'Sample_Bracket')
        self.assertEqual(self.geom.units, 'millimetre')
        self.assertEqual(self.geom.unit_scale_mm, 1.0)

    def test_bounding_box(self):
        # Ground truth from the OpenCASCADE kernel that wrote the file:
        # 80 x 63 x 25 mm.
        self.assertEqual(self.geom.dimensions, (80.0, 63.0, 25.0))

    def test_topology_counts(self):
        self.assertEqual(self.geom.solid_count, 1)
        self.assertEqual(self.geom.face_count, 24)
        self.assertEqual(self.geom.plane_count, 13)

    def test_cylindrical_features(self):
        # The bracket was authored with these diameters, plus R8 corner
        # rounds which also appear as cylindrical faces (dia 16).
        self.assertEqual(self.geom.cylindrical_diameters,
                         [1.5, 6.5, 10.0, 16.0, 20.0])
        self.assertEqual(self.geom.min_cylindrical_diameter, 1.5)

    def test_step_without_solid_geometry_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'empty.step')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write("ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\n"
                             "END-ISO-10303-21;\n")
            geom = read_cad(path)
        self.assertTrue(geom.readable)
        self.assertFalse(geom.has_measurable_geometry)
        self.assertTrue(geom.read_notes)


class TestStlReader(unittest.TestCase):

    def test_cube_volume_and_area_are_exact(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'cube.stl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(cube_stl(10.0))
            geom = read_cad(path)

        self.assertEqual(geom.triangle_count, 12)
        self.assertAlmostEqual(geom.volume_mm3, 1000.0, places=3)
        self.assertAlmostEqual(geom.surface_area_mm2, 600.0, places=3)
        self.assertTrue(geom.is_watertight)
        self.assertEqual(geom.dimensions, (10.0, 10.0, 10.0))

    def test_open_mesh_is_detected(self):
        text = cube_stl(10.0).split('\n')
        # Drop one facet (7 lines) to leave the mesh open.
        start = text.index('facet normal 0 0 0')
        del text[start:start + 7]
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'open.stl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write('\n'.join(text))
            geom = read_cad(path)
        self.assertEqual(geom.triangle_count, 11)
        self.assertFalse(geom.is_watertight)
        self.assertTrue(geom.read_notes)

    def test_sample_stl_matches_the_step_envelope(self):
        step = read_cad(SAMPLE_STEP)
        mesh = read_cad(SAMPLE_STL)
        self.assertTrue(mesh.is_watertight)
        for a, b in zip(step.dimensions, mesh.dimensions):
            self.assertAlmostEqual(a, b, delta=0.05)

    def test_estimated_mass_uses_real_volume(self):
        mesh = read_cad(SAMPLE_STL)
        expected = (mesh.volume_mm3 / 1000.0) * 2.70
        self.assertAlmostEqual(mesh.estimated_mass_g(2.70), expected, places=6)


class TestUnsupportedFiles(unittest.TestCase):

    def test_vendor_format_is_reported_not_guessed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'part.prt')
            with open(path, 'wb') as handle:
                handle.write(b'\x00binary creo data')
            geom = read_cad(path)
        self.assertFalse(geom.readable)
        self.assertFalse(geom.has_measurable_geometry)
        self.assertIn('STEP', ' '.join(geom.read_notes))

    def test_missing_file_does_not_raise(self):
        geom = read_cad('/no/such/file.step')
        self.assertFalse(geom.readable)
        self.assertTrue(geom.read_notes)


if __name__ == '__main__':
    unittest.main()
