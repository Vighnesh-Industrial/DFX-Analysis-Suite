# DFX Analysis Suite 🏭

**Comprehensive Design for Excellence (DFX) Analysis Tool** for CAD components and assemblies.

Perform automated analysis for:
- **DFA** (Design for Assembly)
- **DFM** (Design for Manufacturability)
- **DFI** (Design for Inspection)
- **DFS** (Design for Serviceability)

---

## 📋 Features

✅ **Multi-format CAD Support**
- STEP (.step, .stp)
- IGES (.iges, .igs)
- Creo Parts (.prt, .asm)
- SolidWorks (.sldprt, .sldasm)
- FreeCAD (.FCStd)
- STL (.stl)

✅ **Comprehensive Analysis**
- Individual component scoring (0-10 scale)
- Assembly-level analysis
- Violation & warning detection
- Actionable recommendations

✅ **Multiple Output Formats**
- Text Reports (.txt)
- JSON (.json) for integration
- CSV (.csv) for Excel
- PDF (.pdf) with charts

✅ **Interactive Web Dashboard**
- Upload CAD files
- Real-time analysis
- Visual score cards
- Export reports

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Vighnesh-Industrial/DFX-Analysis-Suite.git
cd DFX-Analysis-Suite

# Install dependencies
pip install -r requirements.txt

# For Creo/SolidWorks support (optional)
pip install pyassimp  # 3D file parsing
```

### Basic Usage

```python
from dfx_analyzers import ComprehensiveDFXAnalyzer

# Initialize analyzer
analyzer = ComprehensiveDFXAnalyzer("path/to/your/component.STEP")

# Run all analyses
report = analyzer.generate_master_report(dfa_params={
    'num_parts': 1,
    'is_symmetric': True,
    'num_fasteners': 2,
    # ... other parameters
})

print(report)
```

---

## 📤 Supported Input Formats

| Format | Extension | Creo Support | Note |
|--------|-----------|-------------|------|
| STEP | `.step`, `.stp` | ✅ Yes | **Recommended** - Universal CAD format |
| IGES | `.iges`, `.igs` | ✅ Yes | Older but compatible |
| Creo Part | `.prt` | ✅ Yes | Native Creo format (requires conversion) |
| Creo Assembly | `.asm` | ✅ Yes | Full assembly analysis |
| SolidWorks | `.sldprt`, `.sldasm` | ⚠️ Via STEP | Export to STEP first |
| FreeCAD | `.FCStd` | ✅ Yes | Direct support |
| STL/Mesh | `.stl` | ✅ Yes | For 3D printed parts |

### ⚠️ Important: Creo Parts Upload

**Creo native files (.prt, .asm) should be converted to STEP/IGES format for best compatibility:**

```bash
# Option 1: Export from Creo
# In Creo: File → Export → Select STEP format → Save

# Option 2: Use provided conversion script
python scripts/convert_creo_to_step.py input.prt output.STEP
```

---

## 📊 Analysis Outputs

### Example Output Structure

```
DFX_Report_20240909_143522/
├── DFX_Master_Report.txt          # Complete text report
├── DFX_Analysis.json              # Structured data
├── DFX_Analysis.csv               # Excel-compatible
├── DFX_Report.pdf                 # Formatted PDF
├── component_scores.json          # Individual component scores
└── recommendations.txt            # Priority action items
```

### Score Ratings

| Score | Rating | Status |
|-------|--------|--------|
| 9-10 | ⭐⭐⭐ EXCELLENT | Ready for production |
| 7-8.9 | ⭐⭐ GOOD | Minor improvements |
| 5-6.9 | ⭐ FAIR | Needs attention |
| <5 | ⚠️ POOR | Critical issues |

---

## 🎯 DFX Analysis Breakdown

### DFA (Design for Assembly)
**Input:** Component parameters (symmetry, fasteners, handling, tool access)
**Output:** DFA Score (0-10), individual metrics, assembly recommendations

### DFM (Design for Manufacturability)
**Input:** CAD file + manufacturing process (injection molding, CNC, sheet metal, etc.)
**Output:** Violations, warnings, manufacturability score, cost estimates

### DFI (Design for Inspection)
**Input:** CAD file geometry
**Output:** Datum surface accessibility, probe clearance, measurement feasibility

### DFS (Design for Serviceability)
**Input:** Assembly structure + component list
**Output:** Modularity score, disassembly complexity, maintenance accessibility

---

## 💻 Web Dashboard Usage

### Start the Dashboard

```bash
cd web_dashboard
python app.py

# Access at: http://localhost:5000
```

### Upload CAD File

1. Navigate to `http://localhost:5000`
2. Click "Upload CAD File"
3. Select your STEP/IGES/CREO file (max 50MB)
4. Click "Analyze"
5. View results in real-time
6. Download reports

---

## 📁 Repository Structure

```
DFX-Analysis-Suite/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── LICENSE                            # MIT License
├── setup.py                          # Installation script
│
├── dfx_analyzers/
│   ├── __init__.py
│   ├── dfa_analyzer.py               # Design for Assembly
│   ├── dfm_analyzer.py               # Design for Manufacturability
│   ├── dfi_analyzer.py               # Design for Inspection
│   ├── dfs_analyzer.py               # Design for Serviceability
│   ├── master_analyzer.py            # Master orchestrator
│   └── utils/
│       ├── cad_parser.py             # CAD file parsing
│       ├── report_generator.py       # Report creation
│       └── data_models.py            # Data structures
│
├── scripts/
│   ├── convert_creo_to_step.py      # Creo conversion utility
│   ├── batch_analysis.py            # Analyze multiple files
│   └── cli_tool.py                  # Command-line interface
│
├── web_dashboard/
│   ├── app.py                       # Flask application
│   ├── config.py                    # Configuration
│   ├── templates/
│   │   ├── index.html              # Upload page
│   │   ├── analysis.html           # Results page
│   │   └── base.html               # Base template
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── uploads/                    # Temporary file storage
│
├── examples/
│   ├── sample_component.STEP       # Example STEP file
│   ├── sample_assembly.STEP        # Example assembly
│   ├── dfx_params_template.json    # DFA parameter template
│   └── sample_output/
│       ├── DFX_Report_sample.txt
│       ├── DFX_Analysis_sample.json
│       └── DFX_Analysis_sample.csv
│
├── tests/
│   ├── test_dfa.py
│   ├── test_dfm.py
│   ├── test_dfi.py
│   ├── test_dfs.py
│   └── test_integration.py
│
└── docs/
    ├── INSTALLATION.md              # Detailed setup guide
    ├── CAD_FORMAT_SUPPORT.md       # Supported formats
    ├── CREO_INTEGRATION.md         # Creo-specific guide
    ├── API_REFERENCE.md            # API documentation
    └── EXAMPLES.md                 # Usage examples
```

---

## 🔧 Installation Modes

### Mode 1: Python Script (Command-line)
```bash
pip install -r requirements.txt
python -c "from dfx_analyzers import ComprehensiveDFXAnalyzer; ..."
```

### Mode 2: Web Dashboard
```bash
pip install -r requirements_web.txt
cd web_dashboard
python app.py
```

### Mode 3: Docker
```bash
docker build -t dfx-suite .
docker run -p 5000:5000 dfx-suite
```

---

## 📝 Usage Examples

### Example 1: Quick DFA Analysis

```python
from dfx_analyzers import DFAAnalyzer

dfa = DFAAnalyzer("Bracket")
report = dfa.generate_dfa_report(
    num_parts=1,
    is_symmetric=True,
    num_fasteners=2,
    tool_clearance_mm=18
)
print(report)
```

### Example 2: Full CAD Analysis

```python
from dfx_analyzers import ComprehensiveDFXAnalyzer

analyzer = ComprehensiveDFXAnalyzer("housing.STEP")
master_report = analyzer.generate_master_report(
    component_params={
        'num_parts': 1,
        'is_symmetric': True,
        # ... DFA params
    }
)
print(master_report)
```

### Example 3: Batch Analysis

```bash
python scripts/batch_analysis.py --input-dir ./parts --process injection_molding
```

---

## 🎯 Creo Parts - Complete Guide

### Converting Creo Files to STEP

**Method 1: Using Creo GUI**
1. Open `.prt` or `.asm` file in Creo
2. File → Export → Select "STEP" format
3. Click "Save"

**Method 2: Using Python Script**
```bash
python scripts/convert_creo_to_step.py input.prt output.STEP
```

**Method 3: Direct Upload to Dashboard**
- Dashboard automatically detects Creo format
- Converts and analyzes in background
- Results available in minutes

### Assembly Analysis

For Creo assemblies (`.asm`):
```python
analyzer = ComprehensiveDFXAnalyzer("assembly.asm")
# Automatically detects assembly
# Analyzes all components
# Provides assembly-level DFA/DFS scores
```

---

## 📊 Output Report Example

```
╔═══════════════════════════════════════════════════════════════════╗
║                    MASTER DFX ANALYSIS REPORT                    ║
║                   Electronic Housing Assembly                     ║
║                    2024-09-09 14:35:22                            ║
╚═══════════════════════════════════════════════════════════════════╝

Overall DFX Score: 6.8/10
├─ DFA Score: 7.8/10 (GOOD) ⭐⭐
├─ DFM Score: 6.2/10 (NEEDS IMPROVEMENT) ⭐
├─ DFI Score: 5.8/10 (FAIR) ⭐
└─ DFS Score: 7.5/10 (GOOD) ⭐⭐

PRIORITY ACTIONS:
1. 🔴 Increase wall thickness (DFM violation)
2. 🟡 Add 3rd datum surface (DFI critical)
3. 🟡 Add draft angles (DFM violation)
```

---

## 📞 Support

### Documentation
- See `/docs` folder for detailed guides
- CAD format support: `docs/CAD_FORMAT_SUPPORT.md`
- Creo integration: `docs/CREO_INTEGRATION.md`

### Issues & Questions
- GitHub Issues: [Report Bug](https://github.com/Vighnesh-Industrial/DFX-Analysis-Suite/issues)
- Discussions: [Ask Question](https://github.com/Vighnesh-Industrial/DFX-Analysis-Suite/discussions)

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/NewAnalysis`)
3. Commit changes (`git commit -m 'Add new DFX metric'`)
4. Push to branch (`git push origin feature/NewAnalysis`)
5. Open Pull Request

---

**Last Updated:** 2024-09-09  
**Version:** 1.0.0  
**Status:** ✅ Production Ready