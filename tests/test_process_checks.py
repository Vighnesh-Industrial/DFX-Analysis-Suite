"""Every manufacturing process must contribute checks of its own.

Regression: sheet_metal and 3d_printing had thresholds defined but no checks
using them, so both produced output identical to 'general'.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dfx_analyzers import ComprehensiveDFXAnalyzer, read_cad
from dfx_analyzers.cad_reader import measure_overhang
from dfx_analyzers.dfm_analyzer import DFMAnalyzer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'example_parts')
BRACKET = os.path.join(PARTS, 'sample_bracket.STEP')
BRACKET_STL = os.path.join(PARTS, 'sample_bracket.stl')

PROCESSES = ('general', 'cnc_machining', 'injection_molding',
             'sheet_metal', '3d_printing')


def box_faces(x0, y0, z0, dx, dy, dz):
    """The 12 triangles of an axis-aligned box, wound outward."""
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    corners = {
        'zmin': [((x0, y0, z0), (x0, y1, z0), (x1, y1, z0)),
                 ((x0, y0, z0), (x1, y1, z0), (x1, y0, z0))],
        'zmax': [((x0, y0, z1), (x1, y1, z1), (x0, y1, z1)),
                 ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1))],
        'ymin': [((x0, y0, z0), (x1, y0, z0), (x1, y0, z1)),
                 ((x0, y0, z0), (x1, y0, z1), (x0, y0, z1))],
        'ymax': [((x0, y1, z0), (x0, y1, z1), (x1, y1, z1)),
                 ((x0, y1, z0), (x1, y1, z1), (x1, y1, z0))],
        'xmin': [((x0, y0, z0), (x0, y0, z1), (x0, y1, z1)),
                 ((x0, y0, z0), (x0, y1, z1), (x0, y1, z0))],
        'xmax': [((x1, y0, z0), (x1, y1, z0), (x1, y1, z1)),
                 ((x1, y0, z0), (x1, y1, z1), (x1, y0, z1))],
    }
    return [t for face in corners.values() for t in face]


class TestOverhangMeasurement(unittest.TestCase):

    def test_a_flat_bottom_on_the_plate_is_not_an_overhang(self):
        overhang, total = measure_overhang(box_faces(0, 0, 0, 10, 10, 10))
        self.assertAlmostEqual(overhang, 0.0, places=6)
        self.assertAlmostEqual(total, 600.0, places=6)

    def test_a_ledge_above_the_plate_overhangs_by_its_area(self):
        """A 10x10 slab on a 2x2 leg: the slab's whole underside overhangs."""
        mesh = (box_faces(4, 4, 0, 2, 2, 5)        # leg, on the plate
                + box_faces(0, 0, 5, 10, 10, 2))   # slab, held above it
        overhang, total = measure_overhang(mesh)
        self.assertAlmostEqual(overhang, 100.0, places=6)
        # leg 48 mm2 + slab 280 mm2
        self.assertAlmostEqual(total, 328.0, places=6)

    def test_vertical_walls_never_overhang(self):
        walls = box_faces(0, 0, 0, 10, 10, 100)
        overhang, _ = measure_overhang(walls)
        self.assertAlmostEqual(overhang, 0.0, places=6)

    def test_no_triangles_gives_no_measurement(self):
        self.assertEqual(measure_overhang([]), (None, None))

    def test_bracket_overhang_is_reported_as_a_fraction(self):
        geom = read_cad(BRACKET_STL)
        self.assertIsNotNone(geom.overhang_fraction)
        self.assertGreaterEqual(geom.overhang_fraction, 0.0)
        self.assertLessEqual(geom.overhang_fraction, 1.0)

    def test_a_step_file_has_no_overhang_measurement(self):
        self.assertIsNone(read_cad(BRACKET).overhang_fraction)


class TestProcessesDiffer(unittest.TestCase):
    """Each process must produce its own finding set, not a copy of general."""

    def _finding_types(self, process, mesh=None):
        analyzer = DFMAnalyzer(process)
        analyzer.analyze_geometry(read_cad(BRACKET) if mesh is None
                                  else self._paired())
        return ({v['Type'] for v in analyzer.violations}
                | {w['Type'] for w in analyzer.warnings}
                | {n['Type'] for n in analyzer.notes})

    def _paired(self):
        return ComprehensiveDFXAnalyzer(BRACKET, mesh_path=BRACKET_STL).geometry

    def test_all_processes_are_accepted(self):
        for process in PROCESSES:
            analyzer = DFMAnalyzer(process)
            analyzer.analyze_geometry(read_cad(BRACKET))  # must not raise
            self.assertIn('min_feature_size', analyzer.limits())

    def test_injection_moulding_checks_draft(self):
        self.assertIn('Insufficient draft', self._finding_types('injection_molding'))

    def test_cnc_checks_internal_corners(self):
        self.assertIn('Sharp internal corners', self._finding_types('cnc_machining'))

    def test_sheet_metal_says_why_it_cannot_check_without_a_thickness(self):
        self.assertIn('Sheet thickness unknown', self._finding_types('sheet_metal'))

    def test_sheet_metal_checks_against_the_measured_thickness(self):
        types = self._finding_types('sheet_metal', mesh=True)
        self.assertIn('Sheet thickness', types)
        self.assertIn('Feature too small for the sheet', types)

    def test_printing_says_why_it_cannot_measure_overhang_without_a_mesh(self):
        self.assertIn('Overhangs not measured', self._finding_types('3d_printing'))

    def test_printing_measures_overhang_from_a_mesh(self):
        types = self._finding_types('3d_printing', mesh=True)
        self.assertTrue({'Overhangs measured', 'Heavy support burden',
                         'Self-supporting'} & types)

    def test_sheet_metal_is_no_longer_a_copy_of_general(self):
        self.assertNotEqual(self._finding_types('sheet_metal'),
                            self._finding_types('general'))

    def test_printing_is_no_longer_a_copy_of_general(self):
        self.assertNotEqual(self._finding_types('3d_printing'),
                            self._finding_types('general'))


class TestBuildVolume(unittest.TestCase):

    def test_a_part_larger_than_the_build_volume_is_flagged(self):
        geom = read_cad(BRACKET)
        analyzer = DFMAnalyzer('3d_printing')
        analyzer._check_3d_printing(geom, 'Part', envelope=(20.0, 20.0, 20.0))
        self.assertIn('Larger than the build volume',
                      [w['Type'] for w in analyzer.warnings])

    def test_a_part_that_fits_is_not_flagged(self):
        geom = read_cad(BRACKET)
        analyzer = DFMAnalyzer('3d_printing')
        analyzer._check_3d_printing(geom, 'Part', envelope=(300.0, 300.0, 300.0))
        self.assertNotIn('Larger than the build volume',
                         [w['Type'] for w in analyzer.warnings])


if __name__ == '__main__':
    unittest.main()
