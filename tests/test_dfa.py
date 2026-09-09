"""Unit tests for DFA Analyzer"""

import unittest
from dfx_analyzers import DFAAnalyzer

class TestDFAAnalyzer(unittest.TestCase):
    """Test cases for Design for Assembly analyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = DFAAnalyzer("Test Component")
    
    def test_part_reduction_single_part(self):
        """Test part reduction scoring for single part"""
        score = self.analyzer.check_part_reduction(num_parts=1)
        self.assertEqual(score, 10)
    
    def test_part_reduction_multiple_parts(self):
        """Test part reduction scoring for multiple parts"""
        score = self.analyzer.check_part_reduction(num_parts=3)
        self.assertLess(score, 10)
        self.assertGreater(score, 0)
    
    def test_symmetry_symmetric(self):
        """Test symmetry scoring for symmetric part"""
        score = self.analyzer.check_symmetry(is_symmetric=True)
        self.assertEqual(score, 10)
    
    def test_symmetry_with_guides(self):
        """Test symmetry scoring with guides"""
        score = self.analyzer.check_symmetry(has_guides=True)
        self.assertEqual(score, 7)
    
    def test_fastener_no_fasteners(self):
        """Test fastener scoring with no fasteners"""
        score = self.analyzer.check_fasteners(num_fasteners=0, use_snap_fit=True)
        self.assertEqual(score, 10)
    
    def test_handling_with_grip_feature(self):
        """Test handling scoring with grip feature"""
        score = self.analyzer.check_handling(has_grip_feature=True)
        self.assertGreaterEqual(score, 6)
    
    def test_tool_access_sufficient_clearance(self):
        """Test tool access with sufficient clearance"""
        score = self.analyzer.check_tool_access(clearance_mm=20, min_clearance=15)
        self.assertEqual(score, 10)
    
    def test_error_proofing_asymmetric(self):
        """Test error-proofing with asymmetric design"""
        score = self.analyzer.check_error_proofing(is_asymmetric=True)
        self.assertEqual(score, 10)
    
    def test_calculate_dfa_score(self):
        """Test overall DFA score calculation"""
        params = {
            'num_parts': 1,
            'is_symmetric': True,
            'num_fasteners': 2,
            'has_grip_feature': True,
            'tool_clearance_mm': 18
        }
        score, scores = self.analyzer.calculate_dfa_score(**params)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 10)
        self.assertIn('part_reduction', scores)
    
    def test_generate_report(self):
        """Test report generation"""
        params = {
            'num_parts': 1,
            'is_symmetric': True,
            'num_fasteners': 2
        }
        report = self.analyzer.generate_dfa_report(**params)
        self.assertIn('DFA ANALYSIS REPORT', report)
        self.assertIn('Overall DFA Score', report)

if __name__ == '__main__':
    unittest.main()
