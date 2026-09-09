# Creo Integration Guide

## Overview

The DFX Analysis Suite supports Creo files (.prt, .asm) through conversion to STEP format.

## Supported Creo Versions

- Creo 7.0 and higher
- Creo Parametric
- Creo Simulate

## Methods for Converting Creo Files

### Method 1: Direct Conversion in Creo GUI (Recommended)

1. Open your Creo file (.prt or .asm)
2. Go to **File → Export**
3. Select **STEP** format from the dropdown
4. Choose output location and filename
5. Click **Save**

### Method 2: Python Conversion Script

```bash
python scripts/convert_creo_to_step.py input.prt -o output.STEP
```

**Requirements:**
- Creo Parametric installed on the same machine

If Creo is not found the script does not fail silently - it prints the exact
manual export steps instead. There is no way to read a `.prt` file without
PTC's software.

### Method 3: Batch analysis after exporting

Export the parts to STEP first, then analyse the whole folder at once:

```bash
python scripts/batch_analysis.py --input-dir ./exported_step --output-dir ./reports
```

Running the batch over a folder of raw `.prt` files produces a report per file
explaining that the format cannot be measured - it does not skip them silently.

## Upload Creo Files to Web Dashboard

1. Convert .prt/.asm to STEP format (see above)
2. Navigate to `http://localhost:5000`
3. Click "Upload CAD File"
4. Select the STEP file
5. Configure DFA parameters
6. Click "Analyze"

## Assembly Analysis

For Creo assemblies (.asm):

```python
from dfx_analyzers import ComprehensiveDFXAnalyzer

analyzer = ComprehensiveDFXAnalyzer("assembly.STEP")
report = analyzer.generate_master_report({
    'num_parts': 8,
    'is_symmetric': True,
    'num_fasteners': 4
})
```

## Limitations

- Some Creo-specific features may be lost in STEP conversion
- Complex assemblies may require manual verification
- Large files (>100MB) may take longer to process

## Troubleshooting

### Issue: "Creo not found" error

**Solution:** Install Creo or use direct web upload after manual conversion

### Issue: "Permission denied" when converting

**Solution:** Ensure you have write permissions in the output directory

```bash
chmod 755 output_directory  # macOS/Linux
```

### Issue: Missing features after conversion

**Solution:** STEP format may not preserve all Creo features. Consider:
- Using native Creo plugins for DFX analysis
- Exporting specific views/configurations
- Manual review of critical features
