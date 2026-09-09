"""DFX Analysis Suite - Design for Excellence Analysis Tool"""

from .dfa_analyzer import DFAAnalyzer
from .dfm_analyzer import DFMAnalyzer
from .dfi_analyzer import DFIAnalyzer
from .dfs_analyzer import DFSAnalyzer
from .master_analyzer import ComprehensiveDFXAnalyzer

__version__ = "1.0.0"
__author__ = "Vighnesh Industrial"
__all__ = [
    "DFAAnalyzer",
    "DFMAnalyzer",
    "DFIAnalyzer",
    "DFSAnalyzer",
    "ComprehensiveDFXAnalyzer",
]
