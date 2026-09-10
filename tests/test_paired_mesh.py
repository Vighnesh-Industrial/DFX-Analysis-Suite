"""Tests for pairing a STEP file with its STL export.

A STEP file carries features and draft but no wall thickness; a mesh carries
thickness and true volume but no features. Analysed together they give one
report with all of it - provided the two files really are the same model.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dfx_analyzers import ComprehensiveDFXAnalyzer, read_cad
from test_cad_reader import cube_stl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'example_parts')
BRACKET = os.path.join(PARTS, 'sample_bracket.STEP')
BRACKET_STL = os.path.join(PARTS, 'sample_bracket.stl')
HOUSING = os.path.join(PARTS, 'sample_housing.STEP')


class TestPairedMesh(unittest.TestCase):

    def test_step_keeps_its_features_and_gains_thickness(self):
        analyzer = ComprehensiveDFXAnalyzer(BRACKET, mesh_path=BRACKET_STL)
        geom = analyzer.geometry
        # Features and draft still come from the STEP file.
        self.assertEqual(geom.cylindrical_diameters,
                         [1.5, 6.5, 10.0, 16.0, 20.0])
        self.assertTrue(geom.wall_draft_angles())
        # Thickness and volume come from the mesh.
        self.assertIsNotNone(geom.min_wall_thickness_mm)
        self.assertIsNotNone(geom.volume_mm3)
        self.assertEqual(geom.mesh_source, 'sample_bracket.stl')
        self.assertEqual(geom.file_format, 'STEP')

    def test_mass_becomes_available(self):
        geom = ComprehensiveDFXAnalyzer(BRACKET, mesh_path=BRACKET_STL).geometry
        self.assertIsNotNone(geom.estimated_mass_g(2.70))

    def test_views_become_shaded(self):
        analyzer = ComprehensiveDFXAnalyzer(BRACKET, mesh_path=BRACKET_STL)
        self.assertEqual([v['kind'] for v in analyzer.views()],
                         ['shaded'] * 4)

    def test_a_mesh_of_a_different_model_is_refused(self):
        """Pairing the wrong files must not silently report another part's
        wall thickness."""
        analyzer = ComprehensiveDFXAnalyzer(HOUSING, mesh_path=BRACKET_STL)
        geom = analyzer.geometry
        self.assertIsNone(geom.min_wall_thickness_mm)
        self.assertTrue(any('same model' in note for note in geom.read_notes))

    def test_an_unreadable_mesh_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'broken.stl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write('not an stl')
            geom = ComprehensiveDFXAnalyzer(BRACKET, mesh_path=path).geometry
        self.assertIsNone(geom.min_wall_thickness_mm)
        self.assertTrue(any('could not be read' in note
                            for note in geom.read_notes))

    def test_no_mesh_leaves_thickness_unmeasured(self):
        geom = ComprehensiveDFXAnalyzer(BRACKET).geometry
        self.assertIsNone(geom.min_wall_thickness_mm)
        self.assertIsNone(geom.mesh_source)

    def test_a_matching_mesh_of_a_simple_solid_is_adopted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'cube.stl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(cube_stl(10.0))
            mesh = read_cad(path)
        base = read_cad(path)          # same dimensions, so it is accepted
        self.assertTrue(base.adopt_mesh(mesh))
        self.assertAlmostEqual(base.min_wall_thickness_mm, 10.0, places=4)


class TestProcessPrecedence(unittest.TestCase):
    """An explicit --process must beat a parameters file."""

    def setUp(self):
        import analyze
        self.analyze = analyze
        self.params = os.path.join(ROOT, 'examples', 'dfx_params_template.json')

    def test_explicit_flag_wins(self):
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, 'r.json')
            self.analyze.main([BRACKET, '--params', self.params,
                               '--process', 'cnc_machining',
                               '--quiet', '--json', out])
            import json
            with open(out, encoding='utf-8') as handle:
                self.assertEqual(json.load(handle)['process_type'],
                                 'cnc_machining')

    def test_params_file_used_when_no_flag(self):
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, 'r.json')
            self.analyze.main([BRACKET, '--params', self.params,
                               '--quiet', '--json', out])
            import json
            with open(out, encoding='utf-8') as handle:
                self.assertEqual(json.load(handle)['process_type'],
                                 'injection_molding')

    def test_default_when_neither(self):
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, 'r.json')
            self.analyze.main([BRACKET, '--quiet', '--json', out])
            import json
            with open(out, encoding='utf-8') as handle:
                self.assertEqual(json.load(handle)['process_type'], 'general')

    def test_missing_mesh_is_an_error_not_a_crash(self):
        self.assertEqual(
            self.analyze.main([BRACKET, '--mesh', '/no/such.stl', '--quiet']), 2)


if __name__ == '__main__':
    unittest.main()
