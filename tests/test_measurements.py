"""Tests for the geometric measurements: draft, thickness, assembly structure.

Every expectation here is ground truth from how the fixtures were authored in
scripts/generate_sample_parts.py, or exact analytic geometry.
"""

import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers.cad_reader import read_cad, measure_wall_thickness
from dfx_analyzers.dfm_analyzer import DFMAnalyzer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'example_parts')
BRACKET = os.path.join(PARTS, 'sample_bracket.STEP')
BRACKET_STL = os.path.join(PARTS, 'sample_bracket.stl')
HOUSING = os.path.join(PARTS, 'sample_housing.STEP')
ASSEMBLY = os.path.join(PARTS, 'sample_assembly.STEP')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_cad_reader import cube_stl


class TestDraftMeasurement(unittest.TestCase):
    """The housing is built with an exact 2 degree taper; the bracket is a
    machined part with vertical walls."""

    def test_drafted_part_reports_its_actual_angle(self):
        geom = read_cad(HOUSING)
        angles = geom.wall_draft_angles()
        self.assertTrue(angles, 'no wall faces were resolved')
        for angle in angles:
            self.assertAlmostEqual(angle, 2.0, delta=0.05)
        self.assertEqual(geom.undrafted_wall_count(1.0), 0)

    def test_vertical_walls_report_zero_draft(self):
        geom = read_cad(BRACKET)
        angles = geom.wall_draft_angles()
        self.assertTrue(angles)
        self.assertTrue(all(a < 0.01 for a in angles))
        self.assertEqual(geom.undrafted_wall_count(1.0), len(angles))

    def test_draft_depends_on_the_pull_direction(self):
        geom = read_cad(BRACKET)
        # Pulling along X makes the faces that were walls into floors, so a
        # different set of faces is considered.
        self.assertNotEqual(geom.wall_draft_angles((0.0, 0.0, 1.0)),
                            geom.wall_draft_angles((1.0, 0.0, 0.0)))

    def test_zero_pull_vector_is_rejected_not_crashed(self):
        self.assertEqual(read_cad(BRACKET).wall_draft_angles((0.0, 0.0, 0.0)), [])

    def test_undrafted_part_fails_the_moulding_check(self):
        analyzer = DFMAnalyzer('injection_molding')
        analyzer.analyze_geometry(read_cad(BRACKET))
        self.assertIn('Insufficient draft', [v['Type'] for v in analyzer.violations])

    def test_drafted_part_passes_the_moulding_check(self):
        analyzer = DFMAnalyzer('injection_molding')
        analyzer.analyze_geometry(read_cad(HOUSING))
        self.assertNotIn('Insufficient draft', [v['Type'] for v in analyzer.violations])
        # A pass is recorded as a note, which must not cost score.
        self.assertIn('Draft confirmed', [n['Type'] for n in analyzer.notes])


class TestWallThickness(unittest.TestCase):

    def test_cube_thickness_is_its_side_length(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'cube.stl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(cube_stl(10.0))
            geom = read_cad(path)
        self.assertAlmostEqual(geom.min_wall_thickness_mm, 10.0, places=4)
        self.assertGreater(geom.wall_thickness_rays, 0)

    def test_thin_plate_thickness(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'plate.stl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(cube_stl(1.5))
            geom = read_cad(path)
        self.assertAlmostEqual(geom.min_wall_thickness_mm, 1.5, places=4)

    def test_thin_wall_raises_a_violation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'thin.stl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(cube_stl(0.8))
            geom = read_cad(path)
        analyzer = DFMAnalyzer('injection_molding')
        analyzer.analyze_geometry(geom)
        violations = [v['Type'] for v in analyzer.violations]
        self.assertIn('Thin wall', violations)

    def test_step_files_have_no_thickness_rather_than_a_guess(self):
        geom = read_cad(BRACKET)
        self.assertIsNone(geom.min_wall_thickness_mm)

    def test_thickness_needs_a_real_mesh(self):
        self.assertEqual(measure_wall_thickness([]), (None, 0))


class TestAssemblyStructure(unittest.TestCase):

    def test_assembly_part_count_is_read_from_the_file(self):
        geom = read_cad(ASSEMBLY)
        self.assertTrue(geom.is_assembly)
        self.assertEqual(geom.assembly_instance_count, 2)
        self.assertEqual(geom.part_count, 2)

    def test_single_part_is_not_an_assembly(self):
        geom = read_cad(BRACKET)
        self.assertFalse(geom.is_assembly)
        self.assertEqual(geom.part_count, 1)

    def test_assembly_bounding_box_carries_a_caveat(self):
        geom = read_cad(ASSEMBLY)
        self.assertTrue(any('placement transforms' in note
                            for note in geom.read_notes))

    def test_shelled_surface_model_still_counts_as_one_body(self):
        geom = read_cad(HOUSING)
        self.assertEqual(geom.solid_count, 0)
        self.assertTrue(geom.has_solid_body)
        self.assertEqual(geom.part_count, 1)


class TestBoundingBoxAccuracy(unittest.TestCase):
    """Regression: the bounding box once included surface placement origins,
    which can sit outside the solid and overstated the bracket by 7 mm."""

    def test_bracket_box_matches_the_authored_size(self):
        self.assertEqual(read_cad(BRACKET).dimensions, (80.0, 63.0, 25.0))

    def test_housing_box_matches_the_authored_size(self):
        self.assertEqual(read_cad(HOUSING).dimensions, (60.0, 40.0, 20.0))


if __name__ == '__main__':
    unittest.main()
