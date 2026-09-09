"""Design for Assembly (DFA) Analyzer"""

class DFAAnalyzer:
    """Analyzes components for assembly ease and efficiency."""
    
    def __init__(self, component_name):
        self.component = component_name
        self.scores = {}
        self.weight = {
            'part_reduction': 0.15,
            'symmetry': 0.15,
            'fasteners': 0.20,
            'handling': 0.15,
            'insertion': 0.15,
            'tool_access': 0.10,
            'error_proofing': 0.10
        }
    
    def check_part_reduction(self, combined=False, num_parts=1):
        """Score: 0-10, Higher is better"""
        if combined:
            return 10
        elif num_parts == 1:
            return 10
        else:
            return max(0, 10 - (num_parts * 2))
    
    def check_symmetry(self, is_symmetric=False, has_guides=False):
        """Check if component is symmetric or has orientation guides"""
        if is_symmetric:
            return 10
        elif has_guides:
            return 7
        else:
            return 3
    
    def check_fasteners(self, num_fasteners=0, use_snap_fit=False, standardized=False):
        """Lower fastener count = higher score"""
        if use_snap_fit:
            return 10
        score = max(0, 10 - (num_fasteners * 1.5))
        if standardized:
            score += 2
        return min(10, score)
    
    def check_handling(self, has_grip_feature=False, part_mass_g=500, fragile=False):
        """Evaluate ease of handling"""
        if fragile:
            return 2
        if has_grip_feature:
            score = 8
        else:
            score = 5
        
        if part_mass_g < 50 or part_mass_g > 2000:
            score -= 2
        return max(0, score)
    
    def check_insertion_motion(self, straight_line=True, rotation_needed=False, depth_mm=0):
        """Straight-line insertion is best"""
        if straight_line and not rotation_needed:
            if depth_mm < 50:
                return 10
            else:
                return 7
        else:
            return 3
    
    def check_tool_access(self, clearance_mm=0, min_clearance=15):
        """Check tool clearance"""
        if clearance_mm >= min_clearance:
            return 10
        elif clearance_mm >= min_clearance * 0.7:
            return 6
        else:
            return 2
    
    def check_error_proofing(self, is_asymmetric=False, has_keying=False, unique_features=False):
        """Prevent incorrect assembly"""
        if is_asymmetric or has_keying or unique_features:
            return 10
        else:
            return 3
    
    def calculate_dfa_score(self, **params):
        """Calculate overall DFA score (0-10)"""
        scores = {
            'part_reduction': self.check_part_reduction(
                combined=params.get('combined', False),
                num_parts=params.get('num_parts', 1)
            ),
            'symmetry': self.check_symmetry(
                is_symmetric=params.get('is_symmetric', False),
                has_guides=params.get('has_guides', False)
            ),
            'fasteners': self.check_fasteners(
                num_fasteners=params.get('num_fasteners', 0),
                use_snap_fit=params.get('use_snap_fit', False),
                standardized=params.get('fasteners_standardized', False)
            ),
            'handling': self.check_handling(
                has_grip_feature=params.get('has_grip_feature', False),
                part_mass_g=params.get('part_mass_g', 500),
                fragile=params.get('fragile', False)
            ),
            'insertion': self.check_insertion_motion(
                straight_line=params.get('straight_line_insertion', True),
                rotation_needed=params.get('rotation_needed', False),
                depth_mm=params.get('insertion_depth_mm', 0)
            ),
            'tool_access': self.check_tool_access(
                clearance_mm=params.get('tool_clearance_mm', 15),
                min_clearance=params.get('min_clearance', 15)
            ),
            'error_proofing': self.check_error_proofing(
                is_asymmetric=params.get('is_asymmetric', False),
                has_keying=params.get('has_keying', False),
                unique_features=params.get('unique_features', False)
            )
        }
        
        self.scores = scores
        weighted_score = sum(scores[k] * self.weight[k] for k in scores.keys())
        return weighted_score, scores
    
    def generate_dfa_report(self, **params):
        """Generate detailed DFA report"""
        overall_score, scores = self.calculate_dfa_score(**params)
        rule = "=" * 74

        report = "\n%s\nDFA ANALYSIS REPORT - %s\nDesign for Assembly\n%s\n" % (
            rule, self.component, rule)
        report += "\nOverall DFA Score: %.1f/10   (%s)\n" % (
            overall_score, self._get_rating(overall_score))
        report += "\nIndividual scores (weighted):\n"

        labels = [
            ('part_reduction', 'Part reduction'),
            ('symmetry', 'Symmetry'),
            ('fasteners', 'Fastener design'),
            ('handling', 'Handling'),
            ('insertion', 'Insertion motion'),
            ('tool_access', 'Tool access'),
            ('error_proofing', 'Error-proofing'),
        ]
        for key, label in labels:
            report += "  %-18s %5.1f/10   (%2.0f%% weight)   %s\n" % (
                label + ':', scores[key], self.weight[key] * 100,
                self._bar(scores[key]))

        report += ("\nNote: DFA scores come from the parameters supplied, not "
                   "from the CAD file.\n      Answer them for the part in its "
                   "installed position for a meaningful score.\n")
        return report

    @staticmethod
    def _bar(score, width=10):
        filled = int(round((score / 10.0) * width))
        return "[" + "#" * filled + "." * (width - filled) + "]"

    def _get_rating(self, score):
        if score >= 9:
            return "EXCELLENT"
        if score >= 7:
            return "GOOD"
        if score >= 5:
            return "FAIR"
        return "NEEDS IMPROVEMENT"
