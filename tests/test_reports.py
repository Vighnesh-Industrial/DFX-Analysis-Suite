"""End-to-end report tests, including the Windows encoding regression."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers import ComprehensiveDFXAnalyzer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_STEP = os.path.join(ROOT, 'example_parts', 'sample_bracket.STEP')
SAMPLE_STL = os.path.join(ROOT, 'example_parts', 'sample_bracket.stl')

PARAMS = {
    'num_parts': 1,
    'num_fasteners': 4,
    'is_symmetric': True,
    'tool_clearance_mm': 18,
}


class TestMasterReport(unittest.TestCase):

    def setUp(self):
        self.analyzer = ComprehensiveDFXAnalyzer(
            SAMPLE_STEP, process_type='cnc_machining')
        self.report = self.analyzer.generate_master_report(dict(PARAMS))

    def test_report_contains_every_section(self):
        for heading in ('MASTER DFX ANALYSIS REPORT', 'MEASURED GEOMETRY',
                        'DFA ANALYSIS REPORT', 'DFM ANALYSIS REPORT',
                        'DFI ANALYSIS REPORT', 'DFS ANALYSIS REPORT',
                        'SUMMARY'):
            self.assertIn(heading, self.report)

    def test_report_states_measured_geometry(self):
        self.assertIn('80.00 x 63.00 x 25.00 mm', self.report)
        self.assertIn('Sample_Bracket', self.report)

    def test_report_survives_a_windows_console_and_file(self):
        """Regression: reports used box-drawing characters and emoji, which
        crashed open(path, 'w') on Windows with a cp1252 charmap error."""
        self.report.encode('cp1252')
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'report.txt')
            with open(path, 'w', encoding='cp1252') as handle:
                handle.write(self.report)
            self.assertTrue(os.path.getsize(path) > 0)

    def test_findings_are_not_empty_for_a_part_with_known_issues(self):
        """The sample bracket is authored with real DFX problems; a report
        with no findings would mean the analysis never read the file."""
        self.assertTrue(self.analyzer.dfm_analyzer.violations)
        self.assertTrue(self.analyzer.dfi_analyzer.inspection_issues)

    def test_scores_are_in_range(self):
        scores = self.analyzer.scores()
        for key in ('dfa', 'dfm', 'dfi', 'dfs', 'composite'):
            self.assertIsNotNone(scores[key])
            self.assertGreaterEqual(scores[key], 0.0)
            self.assertLessEqual(scores[key], 10.0)

    def test_result_is_json_serialisable(self):
        payload = json.dumps(self.analyzer.to_dict(dict(PARAMS)))
        self.assertIn('Sample_Bracket', payload)


class TestMeshReport(unittest.TestCase):

    def test_mesh_report_declares_its_reduced_check_set(self):
        analyzer = ComprehensiveDFXAnalyzer(SAMPLE_STL, process_type='cnc_machining')
        report = analyzer.generate_master_report(dict(PARAMS))
        self.assertIn('Tessellated source', report)
        report.encode('cp1252')


class TestUnreadableInput(unittest.TestCase):

    def test_vendor_file_produces_a_report_that_says_why(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'part.prt')
            with open(path, 'wb') as handle:
                handle.write(b'\x00not a step file')
            analyzer = ComprehensiveDFXAnalyzer(path)
            report = analyzer.generate_master_report({})
        self.assertIn('Export the model as STEP', report)
        report.encode('cp1252')


if __name__ == '__main__':
    unittest.main()
