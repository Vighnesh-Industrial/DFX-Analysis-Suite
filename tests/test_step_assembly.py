"""Tests for STEP assembly placement.

The transform maths is checked directly, and then against the sample
assembly whose true extents are known from the kernel that wrote it.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers.cad_reader import read_cad, read_step_edges
from dfx_analyzers.step_assembly import (IDENTITY, ORIGIN, apply, axis_frame,
                                         compose, invert, is_identity,
                                         read_step_assembly)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'example_parts')
ASSEMBLY = os.path.join(PARTS, 'sample_assembly.STEP')
BRACKET = os.path.join(PARTS, 'sample_bracket.STEP')


class TestTransformMaths(unittest.TestCase):

    def test_identity_leaves_a_point_alone(self):
        transform = (IDENTITY, ORIGIN)
        self.assertTrue(is_identity(transform))
        self.assertEqual(apply(transform, (1.0, 2.0, 3.0)), (1.0, 2.0, 3.0))

    def test_translation(self):
        transform = axis_frame((10.0, 0.0, 5.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        self.assertEqual(apply(transform, (1.0, 2.0, 3.0)), (11.0, 2.0, 8.0))

    def test_rotation_about_x(self):
        """A frame whose local Z points along world -Y."""
        transform = axis_frame(ORIGIN, (0.0, -1.0, 0.0), (1.0, 0.0, 0.0))
        moved = apply(transform, (0.0, 0.0, 1.0))
        for actual, expected in zip(moved, (0.0, -1.0, 0.0)):
            self.assertAlmostEqual(actual, expected, places=9)

    def test_inverse_undoes_a_transform(self):
        transform = axis_frame((3.0, -2.0, 7.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        point = (1.5, -4.0, 2.25)
        restored = apply(invert(transform), apply(transform, point))
        for actual, expected in zip(restored, point):
            self.assertAlmostEqual(actual, expected, places=9)

    def test_compose_applies_inner_first(self):
        lift = axis_frame((0.0, 0.0, 5.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        shift = axis_frame((2.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        combined = compose(lift, shift)
        self.assertEqual(apply(combined, ORIGIN), (2.0, 0.0, 5.0))

    def test_a_frame_stays_orthonormal_when_the_reference_is_not(self):
        """The reference direction need not be perpendicular to the axis."""
        transform = axis_frame(ORIGIN, (0.0, 0.0, 1.0), (1.0, 0.0, 0.7))
        rotation = transform[0]
        columns = [tuple(rotation[row][col] for row in range(3))
                   for col in range(3)]
        for column in columns:
            self.assertAlmostEqual(math.sqrt(sum(c * c for c in column)),
                                   1.0, places=9)
        self.assertAlmostEqual(sum(a * b for a, b in zip(columns[0], columns[2])),
                               0.0, places=9)


class TestAssemblyPlacement(unittest.TestCase):

    def test_components_are_found_and_placed(self):
        geom = read_cad(ASSEMBLY)
        self.assertTrue(geom.components_placed)
        self.assertEqual(geom.dimensions, (60.0, 40.0, 28.0))

    def test_edges_are_placed_too_so_views_show_the_assembly(self):
        """Every component's edges must land in assembly coordinates, or the
        views draw the parts piled on the origin."""
        edges = read_step_edges(ASSEMBLY)
        self.assertTrue(edges)
        highest = max(point[2] for line in edges for point in line)
        lowest = min(point[2] for line in edges for point in line)
        self.assertAlmostEqual(highest, 28.0, delta=0.01)
        self.assertAlmostEqual(lowest, 0.0, delta=0.01)

    def test_a_single_part_reports_no_components(self):
        with open(BRACKET, 'r', encoding='utf-8') as handle:
            text = handle.read()
        from dfx_analyzers.cad_reader import _step_statements
        data = text[text.find('DATA;') + 5:]
        placement = read_step_assembly(BRACKET, _step_statements(data))
        self.assertFalse(placement.is_assembly)
        self.assertEqual(placement.component_reps, [])

    def test_unknown_point_is_returned_unchanged(self):
        with open(BRACKET, 'r', encoding='utf-8') as handle:
            text = handle.read()
        from dfx_analyzers.cad_reader import _step_statements
        data = text[text.find('DATA;') + 5:]
        placement = read_step_assembly(BRACKET, _step_statements(data))
        self.assertEqual(placement.place('999999', (1.0, 2.0, 3.0)),
                         (1.0, 2.0, 3.0))

    def test_oversized_file_is_skipped(self):
        placement = read_step_assembly(ASSEMBLY, iter([]), max_bytes=10)
        self.assertFalse(placement.is_assembly)

    def test_missing_file_is_skipped(self):
        placement = read_step_assembly('/no/such.step', iter([]))
        self.assertFalse(placement.is_assembly)


if __name__ == '__main__':
    unittest.main()


class TestPerComponentMeasurement(unittest.TestCase):
    """Each component is measured in its own right, in assembly coordinates."""

    @classmethod
    def setUpClass(cls):
        cls.geom = read_cad(ASSEMBLY)

    def test_each_component_is_measured_separately(self):
        by_name = {c.label: c for c in self.geom.components}
        self.assertEqual(set(by_name), {'base_plate', 'top_cover', 'riser_post'})
        # Authored sizes, with the post rotated 90 degrees about X.
        self.assertEqual(by_name['base_plate'].dimensions, (60.0, 40.0, 5.0))
        self.assertEqual(by_name['top_cover'].dimensions, (50.0, 30.0, 3.0))
        self.assertEqual(by_name['riser_post'].dimensions, (10.0, 10.0, 20.0))

    def test_each_component_is_a_single_closed_solid(self):
        for component in self.geom.components:
            self.assertEqual(component.solid_count, 1)
            self.assertEqual(component.face_count, 6)

    def test_a_single_part_has_no_components(self):
        self.assertEqual(read_cad(BRACKET).components, [])


class TestPerComponentFindings(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from dfx_analyzers import ComprehensiveDFXAnalyzer
        cls.analyzer = ComprehensiveDFXAnalyzer(
            ASSEMBLY, process_type='injection_molding')
        cls.report = cls.analyzer.generate_master_report({'num_fasteners': 6})

    def test_findings_name_the_component_not_the_assembly(self):
        parts = {v['Part'] for v in self.analyzer.dfm_analyzer.violations}
        self.assertTrue(parts)
        self.assertIn('riser_post', parts)
        self.assertNotIn('Sample_Assembly', parts)

    def test_every_component_is_checked(self):
        tally = self.analyzer.findings_by_component()
        self.assertEqual(set(tally),
                         {'base_plate', 'top_cover', 'riser_post'})

    def test_report_carries_a_component_breakdown(self):
        self.assertIn('COMPONENTS', self.report)
        for name in ('base_plate', 'top_cover', 'riser_post'):
            self.assertIn(name, self.report)
        self.report.encode('cp1252')

    def test_score_is_the_mean_across_components(self):
        """Adding components must not by itself lower the score."""
        tally = self.analyzer.findings_by_component()
        expected = []
        for counts in tally.values():
            expected.append(max(0.0, 10.0 - counts['violations'] * 1.5
                                - counts['warnings'] * 0.4))
        self.assertAlmostEqual(self.analyzer.scores()['dfm'],
                               sum(expected) / len(expected), places=6)

    def test_serviceability_stays_assembly_level(self):
        parts = {i['Component']
                 for i in self.analyzer.dfs_analyzer.serviceability_issues}
        self.assertIn('Sample_Assembly', parts)

    def test_html_report_lists_the_components(self):
        html = self.analyzer.to_html({})
        self.assertIn('Components', html)
        self.assertIn('riser_post', html)
