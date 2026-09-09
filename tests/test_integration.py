"""Integration tests for DFX Analysis Suite"""

import unittest
import os
import tempfile
from dfx_analyzers import ComprehensiveDFXAnalyzer

class TestIntegration(unittest.TestCase):
    """Integration test cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
    
    def test_comprehensive_analyzer_initialization(self):
        """Test comprehensive analyzer initialization"""
        # Create a dummy file
        test_file = os.path.join(self.test_dir, 'test.STEP')
        with open(test_file, 'w') as f:
            f.write('ISO-10303-21;')
        
        analyzer = ComprehensiveDFXAnalyzer(test_file)
        self.assertIsNotNone(analyzer.dfa_analyzer)
        self.assertIsNotNone(analyzer.dfm_analyzer)
        self.assertIsNotNone(analyzer.dfi_analyzer)
        self.assertIsNotNone(analyzer.dfs_analyzer)
    
    def test_master_report_generation(self):
        """Test master report generation"""
        test_file = os.path.join(self.test_dir, 'test.STEP')
        with open(test_file, 'w') as f:
            f.write('ISO-10303-21;')
        
        analyzer = ComprehensiveDFXAnalyzer(test_file)
        params = {'num_parts': 1, 'is_symmetric': True}
        report = analyzer.generate_master_report(params)
        
        self.assertIn('MASTER DFX ANALYSIS REPORT', report)
        self.assertIn('DFA ANALYSIS REPORT', report)
        self.assertIn('DFM ANALYSIS REPORT', report)
        self.assertIn('DFI ANALYSIS REPORT', report)
        self.assertIn('Design for Serviceability', report)

if __name__ == '__main__':
    unittest.main()
