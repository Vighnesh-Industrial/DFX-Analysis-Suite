# DFX Analysis Suite

Automated **Design for Excellence** analysis for CAD parts:

| Discipline | What it covers | Driven by |
|---|---|---|
| **DFM** | Design for Manufacturability | Wall thickness, draft angle and feature sizes measured from the CAD file |
| **DFI** | Design for Inspection | Probe access and feature sizes measured from the CAD file |
| **DFA** | Design for Assembly | Parameters you supply |
| **DFS** | Design for Serviceability | Your parameters, sharpened by measured mass and size |

The analysis core has **no third-party dependencies**. If you have Python, you
can run it right now:

```bash
python analyze.py example_parts/sample_bracket.STEP --process cnc_machining
```

---

**New to it? [docs/WORKFLOW.md](docs/WORKFLOW.md) walks through exporting from
your CAD system and running a study on your own parts and assemblies, step by
step.**

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

## The web dashboard

Upload a file, pick a process, press **ANALYZE**. The analysis runs on a
background worker thread and the page shows live progress, so a dense mesh
does not freeze the browser or time the request out:

```
POST /api/analyze      -> 202 {"job_id": "...", "poll_url": "/api/jobs/..."}
GET  /api/jobs/<id>    -> {"status": "running", "progress": 0.42,
                           "message": "Measuring wall thickness (120 of 261 rays)"}
GET  /api/jobs         -> recent jobs, without their results
```

When the job finishes the page shows the scores, **rendered views of the
part**, the full report, and download links for the text and printable
reports.

---

## Views of the part

Every analysis renders orthographic views - isometric, front, top and right -
straight from the model, with no third-party renderer:

| Source | View | How |
|---|---|---|
| **STL** | Shaded | Triangles back-face culled, depth sorted and flat shaded with a camera-fixed light |
| **STEP** | Wireframe | Drawn from the model's own edge curves; circles and arcs are swept from their centre, axis and sense flag rather than chorded, so holes and fillets look like holes and fillets |

They appear in the dashboard, in the printable HTML report, and can be written
out as SVG files:

```bash
python analyze.py part.STEP --svg-dir views/     # iso.svg, front.svg, top.svg, right.svg
python analyze.py part.stl  --no-views           # skip rendering on a dense mesh
```

A view is only produced when the file supplies the geometry to draw. When it
does not, the report says why instead of showing an empty box.

---

## Assemblies

A STEP assembly stores each component's geometry in its own coordinate system
and records separately where that component sits. The reader follows that
chain - `REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION` to
`ITEM_DEFINED_TRANSFORMATION` - and places every component before anything is
measured, so the bounding box, the envelope checks and the rendered views all
show the assembled model rather than the parts piled on the origin.

The part count used by the DFA score is read from the file's
`NEXT_ASSEMBLY_USAGE_OCCURRENCE` entries, not guessed. If the placements
cannot be resolved, the report says so instead of quietly reporting a wrong
envelope.

**Findings are per component.** You manufacture and inspect components, not
assemblies, so each component is measured in its own right and every DFM and
DFI finding names the component it came from:

```
COMPONENTS

  Component                Envelope (mm)          Findings
  ----------------------------------------------------------------------
  top_cover                50.0 x 30.0 x 3.0      1 violation(s), 0 critical, 2 warning(s)
  base_plate               60.0 x 40.0 x 5.0      1 violation(s), 0 critical, 1 warning(s)
  riser_post               10.0 x 10.0 x 20.0     1 violation(s), 0 critical, 1 warning(s)

  [FAIL] riser_post - Insufficient draft: 4 of 4 wall faces at 0.0 deg or less
```

The DFM and DFI scores are the **mean across components**, so adding parts to
an assembly does not by itself lower the score, and one bad component does not
drag good ones to the floor. Serviceability stays assembly-level, because that
is what you service.

---

## What the tool actually measures

Being precise about this matters: a DFX report that invents numbers is worse
than no report.

### Read directly from the file

| Format | Extensions | What is extracted |
|---|---|---|
| **STEP** | `.step`, `.stp` | Bounding box, units, product name, B-rep face and solid counts, cylindrical / conical / toroidal radii, **per-face draft angle**, **assembly structure with component placements applied** |
| **STL** | `.stl` (ASCII + binary) | Exact volume, surface area, bounding box, watertightness, **true wall thickness by ray casting** |

Both readers are validated against ground truth:

* On the sample bracket the STEP reader reports the same **23 faces, 12 planes
  and 11 cylindrical radii** that the OpenCASCADE kernel does, with identical
  values.
* Draft: the sample housing is modelled with an exact 2 degree taper, and the
  tool measures **2.0 degrees** on all 8 wall faces. The machined bracket
  measures 0.0 degrees, correctly.
* Wall thickness: a 10 mm cube measures **9.999999 mm**, and STL volume matches
  the exact solid volume to within 0.01%.
* Assemblies: the three-part sample, one component of which is rotated 90
  degrees, measures **60 x 40 x 28 mm** - the same as the kernel reports.

### Draft angle

Draft is measured per face against a pull direction you choose (`--pull X|Y|Z`),
by resolving each face's surface normal out of the STEP file. It is not
inferred from the presence of conical faces - tapering a prismatic part
produces slanted *planes*, not cones, so that shortcut misses most real draft.

### Wall thickness

For a closed mesh, a ray is fired from the centre of a sample of faces along
the inward normal, and the distance to the first face it meets is the local
wall thickness. The result is the thinnest wall **found** by sampling, not a
proven global minimum, and the report says how many rays were cast.

STEP files carry no thickness figure. Export an STL of the same model
alongside and pass it with `--mesh`, and the STEP supplies the features and
draft while the mesh supplies thickness, true volume and mass - one report
with all of it:

```bash
python analyze.py part.step --mesh part.stl --process cnc_machining
```

The two files are checked against each other first: if their bounding boxes
disagree, the mesh is refused rather than reporting another part's wall
thickness. In the dashboard it is the **Paired STL** upload field, and
`batch_analysis.py` pairs `part.step` with `part.stl` automatically.

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
  --mesh PART.stl         a paired STL of the same model, for wall thickness
  --name NAME             component name for the report
  --params FILE.json      DFA/DFS answers (see examples/dfx_params_template.json)
  --output REPORT.txt     write the text report
  --html REPORT.html      write a printable report (opens in any browser)
  --json RESULTS.json     write machine-readable results
  --pull {X,Y,Z}          mould pull direction for the draft check
  --svg-dir DIR           write each rendered view as an SVG file
  --no-views              skip rendering views (faster on dense meshes)
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
geom.min_wall_thickness_mm      # measured by ray casting, None for STEP
geom.wall_draft_angles()        # per-face draft, degrees from the pull axis
geom.undrafted_wall_count(1.0)  # walls with less than 1 degree of draft
geom.part_count                 # read from a STEP assembly
geom.estimated_mass_g(2.70)     # None when volume is unknown - never guessed
```

---

## Scoring

Each discipline scores out of 10, and the composite is their mean.

* **DFA** - weighted average of seven assembly factors (part reduction,
  symmetry, fasteners, handling, insertion, tool access, error-proofing).
* **DFM / DFI** - start at 10 and lose **1.5** per violation or critical
  finding and **0.4** per warning. Checks that ran and passed are recorded
  separately as `[INFO]` and cost nothing. When the file carries no measurable
  geometry these come back as **n/a**, not as a high score - a part must never
  look good because nothing could be checked.
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

### Getting a PDF

Open the HTML report and print it (**Ctrl+P**, then *Save as PDF*). The page
carries a print stylesheet that drops the page chrome, so it prints cleanly.
A PDF holds exactly the same information as the HTML report - it is a
container, not an extra source of data - so there is no separate PDF export
to install or maintain.

---

## Project layout

```
analyze.py                  Command-line entry point (no dependencies)
setup.bat / setup.sh        One-time environment setup
run_analysis.bat            Analyse a part on Windows
run_dashboard.bat           Start the dashboard on Windows
dfx_analyzers/
  cad_reader.py             STEP and STL geometry extraction
  step_assembly.py          Assembly component placement
  render.py                 Orthographic SVG views
  html_report.py            Printable HTML report
  dfm_analyzer.py           Manufacturability checks
  dfi_analyzer.py           Inspection checks
  dfa_analyzer.py           Assembly scoring
  dfs_analyzer.py           Serviceability scoring
  master_analyzer.py        Runs everything, builds the report
web_dashboard/
  app.py                    Flask dashboard, queues analyses
  jobs.py                   Background job runner with progress
scripts/
  batch_analysis.py         Analyse a folder of parts
  convert_creo_to_step.py   Creo export helper
  generate_sample_parts.py  Regenerates example_parts (needs CadQuery)
example_parts/              sample_bracket (STEP+STL), sample_housing
                            (drafted), sample_assembly (3 placed parts)
tests/                      129 tests
docs/                       Workflow guide, installation, Creo, examples
```

---

## Tests

```bash
python -m unittest discover -s tests     # no dependencies needed
.venv/bin/python -m pytest tests/ -q     # same tests under pytest
```

129 tests. The 17 web-dashboard tests skip automatically when Flask is not
installed.

---

## Requirements

* **Python 3.8+** - that is all the analysis needs.
* `requirements.txt` - Flask, Flask-Cors, Werkzeug, for the dashboard only.
* `requirements-dev.txt` - pytest, and CadQuery for regenerating the samples.

---

## Roadmap

Honest list of what is *not* implemented yet:

* Wall thickness directly from a STEP B-rep. Pair an STL export with `--mesh`
  and the thickness is measured from that instead.
* Hidden-line removal in the wireframe views: STEP views show all edges,
  including those behind the part.
* Jobs live in memory, so a server restart loses them. Fine for a local tool,
  not for a shared deployment.
* Telling a hole from a boss or an external round. A STEP cylindrical face
  does not say which it is without full topology traversal, so they are
  reported together as "cylindrical features".
* Undercut and side-action detection for moulded parts.

---

## License

MIT - see [LICENSE](LICENSE).
