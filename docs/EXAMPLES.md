# Usage Examples - DFX Analysis Suite

## Example 1: Quick DFA Analysis

```python
from dfx_analyzers import DFAAnalyzer

# Create analyzer
dfa = DFAAnalyzer("Electronic Bracket")

# Run analysis with component parameters
report = dfa.generate_dfa_report(
    num_parts=1,
    is_symmetric=True,
    num_fasteners=2,
    has_grip_feature=True,
    tool_clearance_mm=18,
    has_keying=True
)

print(report)
```

## Example 2: Complete CAD Analysis

```python
from dfx_analyzers import ComprehensiveDFXAnalyzer

# Initialize with CAD file
analyzer = ComprehensiveDFXAnalyzer("housing_assembly.STEP")

# Define component parameters
params = {
    'combined': False,
    'num_parts': 1,
    'is_symmetric': True,
    'has_guides': True,
    'num_fasteners': 4,
    'use_snap_fit': False,
    'fasteners_standardized': True,
    'has_grip_feature': True,
    'part_mass_g': 500,
    'fragile': False,
    'straight_line_insertion': True,
    'rotation_needed': False,
    'insertion_depth_mm': 30,
    'tool_clearance_mm': 20,
    'is_asymmetric': False,
    'has_keying': True,
    'unique_features': True
}

# Generate master report
master_report = analyzer.generate_master_report(params)

# Save to file
with open('DFX_Analysis_Report.txt', 'w') as f:
    f.write(master_report)

print(master_report)
```

## Example 3: Batch Analysis

```bash
# Analyze all CAD files in a directory
python scripts/batch_analysis.py --input-dir ./parts --output-dir ./reports
```

## Example 4: Web Dashboard

```bash
# Start the web server
cd web_dashboard
python app.py

# Access in browser
# http://localhost:5000
```

## Example 5: Command-Line Analysis

```python
# Create a simple analysis script

from dfx_analyzers import DFAAnalyzer, DFMAnalyzer

# DFA Analysis
print("=== DFA Analysis ===")
dfa = DFAAnalyzer("Component X")
dfa_report = dfa.generate_dfa_report(
    num_parts=1,
    num_fasteners=2,
    tool_clearance_mm=15
)
print(dfa_report)

# DFM Analysis
print("\n=== DFM Analysis ===")
dfm = DFMAnalyzer(process_type='injection_molding')
dfm.add_violation(
    part_name='Housing',
    issue_type='Wall Thickness',
    value=0.8,
    required=1.5,
    recommendation='Increase to 1.5-2.0mm'
)
dfm_report = dfm.generate_dfm_report()
print(dfm_report)
```

## Example 6: Creo File Analysis

```bash
# Convert Creo file to STEP
python scripts/convert_creo_to_step.py my_part.prt my_part.STEP

# Then analyze
python -c "
from dfx_analyzers import ComprehensiveDFXAnalyzer
analyzer = ComprehensiveDFXAnalyzer('my_part.STEP')
print(analyzer.generate_master_report({'num_parts': 1}))
"
```

## Example 7: Custom Analysis Workflow

```python
from dfx_analyzers import (
    DFAAnalyzer,
    DFMAnalyzer,
    DFIAnalyzer,
    DFSAnalyzer
)

def analyze_component(component_name, cad_file):
    """Custom analysis workflow"""
    
    results = {}
    
    # DFA
    dfa = DFAAnalyzer(component_name)
    results['dfa'] = dfa.generate_dfa_report(
        num_parts=1,
        is_symmetric=True,
        num_fasteners=2
    )
    
    # DFM
    dfm = DFMAnalyzer('cnc_machining')
    results['dfm'] = dfm.generate_dfm_report()
    
    # DFI
    dfi = DFIAnalyzer()
    results['dfi'] = dfi.generate_dfi_report()
    
    # DFS
    dfs = DFSAnalyzer()
    results['dfs'] = dfs.generate_dfs_report()
    
    return results

# Run analysis
results = analyze_component('MyComponent', 'component.STEP')

for analysis_type, report in results.items():
    print(f"\n{'='*60}")
    print(f"{analysis_type.upper()}")
    print(f"{'='*60}")
    print(report)
```
