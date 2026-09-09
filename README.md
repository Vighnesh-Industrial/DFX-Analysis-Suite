# DFX Analysis Suite

Automated **Design for Excellence** analysis for CAD parts:

| Discipline | What it covers | Driven by |
|---|---|---|
| **DFM** | Design for Manufacturability | Geometry measured from the CAD file |
| **DFI** | Design for Inspection | Geometry measured from the CAD file |
| **DFA** | Design for Assembly | Parameters you supply |
| **DFS** | Design for Serviceability | Your parameters, sharpened by measured mass and size |

The analysis core has **no third-party dependencies**. If you have Python, you
can run it right now:

```bash
python analyze.py example_parts/sample_bracket.STEP --process cnc_machining
```

---

## Quick start

### Windows

Double-click, in this order:

1. **`setup.bat`** - creates the virtual environment and installs the web
   dependencies. It uses `python -m pip` throughout and never depends on
   `activate`, so it does not hit the usual *"pip is not recognized"* problem.
2. **`run_analysis.bat`** - analyses the sample bracket and writes
   `DFX_Report.txt`. Pass your own file to analyse it instead:
   `run_analysis.bat "C:\path\to\part.step"`
3. **`run_dashboard.bat`** - starts the web dashboard on
   <http://localhost:5000>.

`run_analysis.bat` works even if `setup.bat` has not been run, because the
command-line analysis needs no installed packages.

### macOS / Linux

```bash
./setup.sh                                          # optional: only the dashboard needs it
python3 analyze.py example_parts/sample_bracket.STEP
.venv/bin/python web_dashboard/app.py               # dashboard on http://localhost:5000
```

---

## What the tool actually measures

Being precise about this matters: a DFX report that invents numbers is worse
than no report.

### Read directly from the file

| Format | Extensions | What is extracted |
|---|---|---|
| **STEP** | `.step`, `.stp` | Bounding box, units, product name, B-rep face and solid counts, cylindrical / conical / toroidal surface radii |
| **STL** | `.stl` (ASCII + binary) | Exact volume, surface area, bounding box, triangle count, watertightness |

The STEP reader is validated against OpenCASCADE: on the sample bracket it
reports the same 24 faces, 13 planes and 10 cylindrical radii that the kernel
does, and the STL volume matches the exact solid volume to within 0.01%.

### Accepted but **not** measurable

`.prt`, `.asm`, `.sldprt`, `.sldasm`, `.iges`, `.igs`, `.fcstd`

These are closed vendor formats. Uploading one produces a report that says so
and tells you to export STEP - it does **not** silently return an empty
analysis. Export from your CAD system with **File > Save As > STEP (AP203 or
AP214)**; see [`docs/CREO_INTEGRATION.md`](docs/CREO_INTEGRATION.md).

### Answered by you, not by the file

Assembly and serviceability questions - symmetry in the installed position,
fastener count, tool clearance, insertion motion - cannot be read from a
single part file. The report labels these clearly so the two kinds of finding
are never confused.

---

## Command line

```bash
python analyze.py PART.step [options]

  --process {general,cnc_machining,injection_molding,sheet_metal,3d_printing}
  --name NAME             component name for the report
  --params FILE.json      DFA/DFS answers (see examples/dfx_params_template.json)
  --output REPORT.txt     write the text report
  --json RESULTS.json     write machine-readable results
  --quiet                 do not print to the screen
```

Batch a whole folder:

```bash
python scripts/batch_analysis.py --input-dir example_parts --process cnc_machining
```

This writes one report per file plus `batch_summary.json` and
`batch_summary.csv` for Excel.

---

## Python API

```python
from dfx_analyzers import ComprehensiveDFXAnalyzer

analyzer = ComprehensiveDFXAnalyzer('part.STEP', process_type='cnc_machining')

print(analyzer.geometry.summary_lines())   # what was measured
print(analyzer.generate_master_report({    # full text report
    'num_parts': 1,
    'is_symmetric': True,
    'num_fasteners': 2,
    'tool_clearance_mm': 18,
}))

analyzer.scores()    # {'dfa': .., 'dfm': .., 'dfi': .., 'dfs': .., 'composite': ..}
analyzer.to_dict()   # JSON-serialisable results
```

Just the geometry:

```python
from dfx_analyzers import read_cad

geom = read_cad('part.STEP')
geom.dimensions                 # (80.0, 63.0, 25.0) mm
geom.cylindrical_diameters      # [1.5, 6.5, 10.0, 16.0, 20.0]
geom.volume_mm3                 # exact for STL, None for STEP
geom.estimated_mass_g(2.70)     # None when volume is unknown - never guessed
```

---

## Scoring

Each discipline scores out of 10, and the composite is their mean.

* **DFA** - weighted average of seven assembly factors (part reduction,
  symmetry, fasteners, handling, insertion, tool access, error-proofing).
* **DFM / DFI** - start at 10 and lose **1.5** per violation or critical
  finding and **0.4** per warning.
* **DFS** - starts at 10 and loses points for fastener count, tight tool
  clearance, handling mass and low modularity.

A score built from fewer checks is flagged as such: analysing a mesh instead
of a STEP file raises a *Tessellated source* warning, because a mesh carries no
feature data and therefore cannot fail the hole, fillet or draft checks.

---

## Example output

```
DFM ANALYSIS REPORT (CNC MACHINING)

VIOLATIONS (1):

  [FAIL] Sample_Bracket - Small cylindrical feature: 1.50 mm diameter
         Required: >= 2.00 mm
         Action:   A 1.50 mm feature needs a fragile small-diameter tool and a
                   slow peck cycle. Open it up to 2.00 mm, or call it out as a
                   drilled pilot with a separate operation.

DFI ANALYSIS REPORT

CRITICAL (1):

  [CRIT] Sample_Bracket - Probe cannot enter
         Feature diameters 1.50 mm are smaller than the 5.0 mm standard touch probe.
         Action:   These features cannot be measured on a CMM. Either enlarge them,
                   accept an optical or pin-gauge check, or mark them as
                   reference-only on the drawing.
```

Report text is plain ASCII on purpose, so it survives a Windows console and a
`cp1252` file handle.

---

## Project layout

```
analyze.py                  Command-line entry point (no dependencies)
setup.bat / setup.sh        One-time environment setup
run_analysis.bat            Analyse a part on Windows
run_dashboard.bat           Start the dashboard on Windows
dfx_analyzers/
  cad_reader.py             STEP and STL geometry extraction
  dfm_analyzer.py           Manufacturability checks
  dfi_analyzer.py           Inspection checks
  dfa_analyzer.py           Assembly scoring
  dfs_analyzer.py           Serviceability scoring
  master_analyzer.py        Runs everything, builds the report
web_dashboard/              Flask upload dashboard
scripts/
  batch_analysis.py         Analyse a folder of parts
  convert_creo_to_step.py   Creo export helper
  generate_sample_parts.py  Regenerates example_parts (needs CadQuery)
example_parts/              Sample bracket, STEP + STL
tests/                      53 tests
docs/                       Installation, Creo integration, examples
```

---

## Tests

```bash
python -m unittest discover -s tests     # no dependencies needed
.venv/bin/python -m pytest tests/ -q     # same tests under pytest
```

53 tests. The 12 web-dashboard tests skip automatically when Flask is not
installed.

---

## Requirements

* **Python 3.8+** - that is all the analysis needs.
* `requirements.txt` - Flask, Flask-Cors, Werkzeug, for the dashboard only.
* `requirements-dev.txt` - pytest, and CadQuery for regenerating the samples.

---

## Roadmap

Honest list of what is *not* implemented yet:

* True wall-thickness measurement (needs a solid-modelling kernel).
* Draft-angle measurement against a stated pull direction.
* Assembly-level DFA from `.asm` structure.
* PDF report export.

---

## License

MIT - see [LICENSE](LICENSE).
