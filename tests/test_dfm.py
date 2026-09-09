"""Unit tests for DFM Analyzer"""

import unittest
from dfx_analyzers import DFMAnalyzer

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

if __name__ == '__main__':
    unittest.main()
