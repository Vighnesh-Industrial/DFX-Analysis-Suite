# Usage Examples - DFX Analysis Suite

## Example 0: Read the geometry only

```python
from dfx_analyzers import read_cad

geom = read_cad('example_parts/sample_bracket.STEP')

print(geom.dimensions)              # (80.0, 63.0, 25.0) millimetres
print(geom.cylindrical_diameters)   # [1.5, 6.5, 10.0, 16.0, 20.0]
print(geom.face_count, geom.solid_count)
print('\n'.join(geom.summary_lines()))
```

Fields that cannot be measured come back as `None`, never as a guess:

```python
geom.volume_mm3          # exact for STL, None for STEP
geom.estimated_mass_g()  # None when the volume is unknown
```

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
analyzer = ComprehensiveDFXAnalyzer("housing_assembly.STEP",
                                    process_type='cnc_machining')

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

# Save to file. Always pass encoding='utf-8': the Windows default is
# cp1252 and will raise UnicodeEncodeError on some characters.
with open('DFX_Analysis_Report.txt', 'w', encoding='utf-8') as f:
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
# Export the Creo file to STEP (needs Creo installed; otherwise the script
# prints the manual File > Save As steps)
python scripts/convert_creo_to_step.py my_part.prt -o my_part.STEP

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

## Example 8: Command-line entry point

```bash
# Text report on screen
python analyze.py example_parts/sample_bracket.STEP --process cnc_machining

# Save both a text report and machine-readable results
python analyze.py part.step --output report.txt --json results.json --quiet

# Supply the DFA/DFS answers from a file
python analyze.py part.step --params examples/dfx_params_template.json
```

## Example 9: Scores as data

```python
from dfx_analyzers import ComprehensiveDFXAnalyzer

analyzer = ComprehensiveDFXAnalyzer('part.STEP', process_type='injection_molding')
analyzer.generate_master_report({'num_parts': 1, 'num_fasteners': 4})

scores = analyzer.scores()
print(scores['composite'], scores['dfm_violations'], scores['dfi_critical'])

for violation in analyzer.dfm_analyzer.violations:
    print(violation['Type'], violation['Value'], '->', violation['Recommendation'])
```

## Example 10: Draft, thickness and assembly structure

```python
from dfx_analyzers import read_cad

housing = read_cad('example_parts/sample_housing.STEP')
housing.wall_draft_angles()            # [2.0, 2.0, ...] degrees
housing.undrafted_wall_count(1.0)      # 0

# Draft depends on the pull direction, so state it
housing.wall_draft_angles(pull=(1.0, 0.0, 0.0))

mesh = read_cad('example_parts/sample_bracket.stl')
mesh.min_wall_thickness_mm             # measured by ray casting
mesh.wall_thickness_rays               # how many samples that came from

assembly = read_cad('example_parts/sample_assembly.STEP')
assembly.is_assembly                   # True
assembly.part_count                    # 2, read from the file
```

## Example 11: A printable report

```python
from dfx_analyzers import ComprehensiveDFXAnalyzer

analyzer = ComprehensiveDFXAnalyzer('part.STEP', process_type='injection_molding')
html = analyzer.to_html({'num_fasteners': 4})

with open('report.html', 'w', encoding='utf-8') as handle:
    handle.write(html)
```

Or from the command line, choosing the pull direction:

```bash
python analyze.py part.STEP --process injection_molding --pull Y --html report.html
```
