# Quick Test Guide

## Test File Included

A sample STEP file is included at: `example_parts/sample_bracket.STEP`

## Quick Start Test

### 1. Start Web Dashboard
```bash
cd web_dashboard
python app.py
```

### 2. Upload Sample File
- Navigate to: http://localhost:5000
- Upload: `example_parts/sample_bracket.STEP`
- Use default DFA parameters or customize
- Click "Analyze"

### 3. View Results
- Master DFX Report will be displayed
- Download the report

## Command-Line Quick Test

```bash
python -c "
from dfx_analyzers import ComprehensiveDFXAnalyzer

analyzer = ComprehensiveDFXAnalyzer('example_parts/sample_bracket.STEP')
report = analyzer.generate_master_report({
    'num_parts': 1,
    'is_symmetric': True,
    'num_fasteners': 2,
    'has_grip_feature': True,
    'tool_clearance_mm': 18,
    'has_keying': True,
    'unique_features': True
})
print(report)
"
```

## Expected Output

You should see a report with:
- Overall DFX Score (0-10)
- Individual DFA, DFM, DFI, DFS scores
- Violations and warnings
- Actionable recommendations

## Next: Test with Your Files

1. Export your Creo assembly to STEP format
2. Place in `example_parts/` directory
3. Upload and analyze
4. Review results
