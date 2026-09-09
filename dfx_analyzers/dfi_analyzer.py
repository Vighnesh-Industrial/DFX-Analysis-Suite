"""Design for Inspection (DFI) Analyzer"""

class DFIAnalyzer:
    """Analyzes components for measurement and inspection feasibility."""
    
    def __init__(self):
        self.inspection_issues = []
        self.cmm_clearance_min = 15  # mm
        self.probe_radius = 5  # mm
    
    def add_critical_issue(self, part_name, issue_type, message, recommendation):
        """Record critical inspection issue"""
        self.inspection_issues.append({
            'Part': part_name,
            'Issue': issue_type,
            'Type': 'CRITICAL',
            'Message': message,
            'Recommendation': recommendation
        })
    
    def add_warning(self, part_name, issue_type, message, recommendation):
        """Record inspection warning"""
        self.inspection_issues.append({
            'Part': part_name,
            'Issue': issue_type,
            'Type': 'WARNING',
            'Message': message,
            'Recommendation': recommendation
        })
    
    def add_info(self, part_name, issue_type, message, recommendation):
        """Record inspection information note"""
        self.inspection_issues.append({
            'Part': part_name,
            'Issue': issue_type,
            'Type': 'INFO',
            'Message': message,
            'Recommendation': recommendation
        })
    
    def generate_dfi_report(self):
        """Generate DFI analysis report"""
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║         DFI ANALYSIS REPORT (Design for Inspection)            ║
╚════════════════════════════════════════════════════════════════╝

FINDINGS ({len(self.inspection_issues)}):
"""
        
        critical = [i for i in self.inspection_issues if i['Type'] == 'CRITICAL']
        warnings = [i for i in self.inspection_issues if i['Type'] == 'WARNING']
        info = [i for i in self.inspection_issues if i['Type'] == 'INFO']
        
        if critical:
            report += f"\n\nCRITICAL ISSUES ({len(critical)}):"
            for issue in critical:
                report += f"\n  🔴 {issue['Part']}: {issue['Message']}"
                report += f"\n     → {issue['Recommendation']}"
        
        if warnings:
            report += f"\n\nWARNINGS ({len(warnings)}):"
            for issue in warnings:
                report += f"\n  🟡 {issue['Part']}: {issue['Message']}"
                report += f"\n     → {issue['Recommendation']}"
        
        if info:
            report += f"\n\nINFORMATION ({len(info)}):"
            for issue in info:
                report += f"\n  ℹ️  {issue['Part']}: {issue['Message']}"
                report += f"\n     → {issue['Recommendation']}"
        
        report += "\n"
        return report
