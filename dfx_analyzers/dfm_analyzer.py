"""Design for Manufacturability (DFM) Analyzer"""

class DFMAnalyzer:
    """Analyzes components for manufacturing feasibility."""
    
    def __init__(self, process_type='general'):
        self.process = process_type
        self.violations = []
        self.warnings = []
        
        self.thresholds = {
            'injection_molding': {
                'min_wall_thickness': 1.5,
                'max_wall_thickness': 5.0,
                'min_draft_angle': 1.0,
                'rib_ratio': 0.6,
                'min_fillet_radius': 0.5
            },
            'cnc_machining': {
                'min_hole_diameter': 2.0,
                'min_feature_size': 1.0,
                'corner_radius_ratio': 1.0,
                'min_slot_width': 2.0
            },
            'sheet_metal': {
                'min_bend_radius_ratio': 1.0,
                'min_hole_diameter_ratio': 1.5,
                'min_flange_ratio': 4.0
            },
            '3d_printing': {
                'min_wall_thickness': 1.0,
                'max_overhang_angle': 45,
                'min_feature_size': 0.5
            }
        }
    
    def add_violation(self, part_name, issue_type, value, required, recommendation):
        """Record a DFM violation"""
        self.violations.append({
            'Part': part_name,
            'Type': issue_type,
            'Value': value,
            'Required': required,
            'Status': 'FAIL',
            'Recommendation': recommendation
        })
    
    def add_warning(self, part_name, issue_type, message, recommendation):
        """Record a DFM warning"""
        self.warnings.append({
            'Part': part_name,
            'Type': issue_type,
            'Status': 'WARNING',
            'Message': message,
            'Recommendation': recommendation
        })
    
    def generate_dfm_report(self):
        """Generate DFM analysis report"""
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║         DFM ANALYSIS REPORT ({self.process.upper()})           ║
╚════════════════════════════════════════════════════════════════╝

VIOLATIONS ({len(self.violations)}):
"""
        for v in self.violations:
            report += f"\n  ❌ {v['Part']} - {v['Type']}: {v.get('Value', 'N/A')} "
            report += f"\n     Recommendation: {v['Recommendation']}"
        
        report += f"\n\nWARNINGS ({len(self.warnings)}):\n"
        for w in self.warnings:
            report += f"\n  ⚠️  {w['Part']} - {w['Type']}"
            report += f"\n     Recommendation: {w['Recommendation']}"
        
        report += "\n"
        return report
