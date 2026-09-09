"""Master Comprehensive DFX Analyzer"""

from datetime import datetime
from .dfa_analyzer import DFAAnalyzer
from .dfm_analyzer import DFMAnalyzer
from .dfi_analyzer import DFIAnalyzer
from .dfs_analyzer import DFSAnalyzer

class ComprehensiveDFXAnalyzer:
    """Master analyzer combining DFA, DFM, DFI, and DFS analyses."""
    
    def __init__(self, cad_file_path):
        self.cad_file = cad_file_path
        self.dfa_analyzer = DFAAnalyzer("Component")
        self.dfm_analyzer = DFMAnalyzer()
        self.dfi_analyzer = DFIAnalyzer()
        self.dfs_analyzer = DFSAnalyzer()
        self.results = {}
    
    def run_all_analyses(self, component_params):
        """Run DFA, DFM, DFI, DFS for a component"""
        results = {
            'DFA': self.dfa_analyzer.generate_dfa_report(**component_params),
            'DFM': self.dfm_analyzer.generate_dfm_report(),
            'DFI': self.dfi_analyzer.generate_dfi_report(),
            'DFS': self.dfs_analyzer.generate_dfs_report()
        }
        return results
    
    def generate_master_report(self, component_params):
        """Generate master DFX report for component"""
        all_results = self.run_all_analyses(component_params)
        
        master_report = f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MASTER DFX ANALYSIS REPORT                                 ║
║                     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

File: {self.cad_file}

{all_results['DFA']}

{all_results['DFM']}

{all_results['DFI']}

{all_results['DFS']}

╔═══════════════════════════════════════════════════════════════════════════════╗
║                          END OF REPORT                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
        
        return master_report
