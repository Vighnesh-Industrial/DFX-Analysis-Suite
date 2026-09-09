"""Design for Serviceability (DFS) Analyzer"""

class DFSAnalyzer:
    """Analyzes assemblies for serviceability and maintenance accessibility."""
    
    def __init__(self):
        self.serviceability_issues = []
        self.modularity_score = 0
        self.accessibility_score = 0
    
    def add_issue(self, component_name, issue_type, message, recommendation, severity='WARNING'):
        """Record serviceability issue"""
        self.serviceability_issues.append({
            'Component': component_name,
            'Issue': issue_type,
            'Type': severity,
            'Message': message,
            'Recommendation': recommendation
        })
    
    def generate_dfs_report(self, overall_score=7.5):
        """Generate Design for Serviceability report"""
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║    Design for Serviceability (DFS) ANALYSIS REPORT             ║
╚════════════════════════════════════════════════════════════════╝

Overall Serviceability Score: {overall_score:.1f}/10

ISSUES FOUND ({len(self.serviceability_issues)}):
"""
        
        for issue in self.serviceability_issues:
            icon = "🔴" if issue['Type'] == 'CRITICAL' else "🟡" if issue['Type'] == 'WARNING' else "ℹ️ "
            report += f"\n  {icon} {issue.get('Component', '')} - {issue['Issue']}"
            report += f"\n     {issue['Message']}"
            report += f"\n     → {issue['Recommendation']}\n"
        
        report += f"\n\nRating: {self._get_serviceability_rating(overall_score)}"
        return report
    
    def _get_serviceability_rating(self, score):
        if score >= 8: return "EXCELLENT (Easy to service) ⭐⭐⭐"
        elif score >= 6: return "GOOD (Moderate serviceability) ⭐⭐"
        elif score >= 4: return "FAIR (Some service challenges) ⭐"
        else: return "POOR (Difficult to service) ⚠️"
