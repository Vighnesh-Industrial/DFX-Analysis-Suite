"""Unit tests for DFM Analyzer"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers import DFMAnalyzer
from dfx_analyzers.cad_reader import read_cad

SAMPLE_STEP = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'example_parts', 'sample_bracket.STEP')

class TestDFMAnalyzer(unittest.TestCase):
    """Test cases for Design for Manufacturability analyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = DFMAnalyzer(process_type='injection_molding')
    
    def test_initialization(self):
        """Test DFM analyzer initialization"""
        self.assertEqual(self.analyzer.process, 'injection_molding')
        self.assertEqual(len(self.analyzer.violations), 0)
        self.assertEqual(len(self.analyzer.warnings), 0)
    
    def test_add_violation(self):
        """Test adding a violation"""
        self.analyzer.add_violation(
            part_name='Housing',
            issue_type='Wall Thickness',
            value=0.8,
            required=1.5,
            recommendation='Increase wall thickness'
        )
        self.assertEqual(len(self.analyzer.violations), 1)
        self.assertEqual(self.analyzer.violations[0]['Part'], 'Housing')
    
    def test_add_warning(self):
        """Test adding a warning"""
        self.analyzer.add_warning(
            part_name='Housing',
            issue_type='Sharp Edge',
            message='Sharp edge detected',
            recommendation='Add fillet'
        )
        self.assertEqual(len(self.analyzer.warnings), 1)
        self.assertEqual(self.analyzer.warnings[0]['Part'], 'Housing')
    
    def test_generate_report(self):
        """Test report generation"""
        self.analyzer.add_violation(
            part_name='Housing',
            issue_type='Wall Thickness',
            value=0.8,
            required=1.5,
            recommendation='Increase wall thickness'
        )
        report = self.analyzer.generate_dfm_report()
        self.assertIn('DFM ANALYSIS REPORT', report)
        self.assertIn('VIOLATIONS', report)

class TestDFMGeometryChecks(unittest.TestCase):
    """The DFM checks must be driven by the CAD file, not by defaults."""

    def setUp(self):
        self.geom = read_cad(SAMPLE_STEP)

    def test_small_feature_raises_a_violation(self):
        analyzer = DFMAnalyzer('cnc_machining')
        analyzer.analyze_geometry(self.geom)
        types = [v['Type'] for v in analyzer.violations]
        self.assertIn('Small cylindrical feature', types)
        # The 1.5 mm pilot hole in the sample part is the offender.
        offender = next(v for v in analyzer.violations
                        if v['Type'] == 'Small cylindrical feature')
        self.assertIn('1.50', offender['Value'])

    def test_tooling_variety_warning(self):
        analyzer = DFMAnalyzer('cnc_machining')
        analyzer.analyze_geometry(self.geom)
        self.assertIn('Tooling variety', [w['Type'] for w in analyzer.warnings])

    def test_unreadable_file_is_reported_not_silently_passed(self):
        analyzer = DFMAnalyzer('cnc_machining')
        analyzer.analyze_geometry(read_cad('/no/such/part.prt'))
        self.assertTrue(analyzer.warnings,
                        'an unreadable file must produce a finding')

    def test_unknown_process_falls_back_to_general_limits(self):
        analyzer = DFMAnalyzer('some_new_process')
        limits = analyzer.limits()
        self.assertIn('min_hole_diameter', limits)
        analyzer.analyze_geometry(self.geom)  # must not raise

    def test_report_is_ascii_only(self):
        analyzer = DFMAnalyzer('cnc_machining')
        analyzer.analyze_geometry(self.geom)
        report = analyzer.generate_dfm_report()
        # cp1252 is the Windows default; a report it cannot encode crashes
        # any plain open(path, 'w') on Windows.
        report.encode('cp1252')
        report.encode('ascii')


if __name__ == '__main__':
    unittest.main()
