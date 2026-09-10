# Working with your own parts and assemblies

A step-by-step guide for running a DFX study on your own CAD, from export to
finished report.

---

## Step 0 - Get the tool (once)

```bash
git clone https://github.com/Vighnesh-Industrial/DFX-Analysis-Suite.git
cd DFX-Analysis-Suite
```

If you already cloned it before, make sure you are on the current code:

```bash
git checkout main
git pull
```

Nothing needs installing to analyse a file. Only the web dashboard needs
Flask, and `setup.bat` (Windows) or `./setup.sh` (macOS/Linux) handles that.

**Check it works** before you point it at your own parts:

```bash
python analyze.py example_parts/sample_bracket.STEP
```

Windows: double-click `run_analysis.bat`.

---

## Step 1 - Export from your CAD system

The tool reads **STEP** and **STL**. Everything else - Creo `.prt`, SolidWorks
`.sldprt`, NX, Inventor - is a closed format that only its own software can
open, so the first step is always an export.

### STEP (always)

| CAD system | How |
|---|---|
| **Creo Parametric** | File > Save As > Save a Copy > Type: **STEP (\*.stp)**. In the options set **AP214** and tick **Solids**. |
| **SolidWorks** | File > Save As > **STEP AP214 (\*.step)**. |
| **NX** | File > Export > **STEP214**. |
| **Inventor** | File > Export > CAD Format > **STEP**, application protocol 214. |
| **Fusion 360** | File > Export > **STEP**. |
| **Onshape** | Right-click the tab > Export > **STEP**. |

Use **AP214** where you have the choice (AP203 works too). Export **solids**,
not surfaces - a surface-only export has no solid model and the report will
tell you so rather than measuring nothing quietly.

### STL (worth it - adds wall thickness)

A STEP file describes faces and edges but carries no wall thickness. Export an
**STL of the same model** as well and the tool measures the true wall
thickness, volume and mass:

* **Creo**: File > Save As > Save a Copy > Type: **STL**. Set **Chord Height**
  to about `0.05` mm.
* **SolidWorks**: Save As > STL > Options > **Fine**, or set deviation to
  `0.05` mm.
* **Fusion / Inventor / NX**: choose a **fine / high** refinement.

A coarse STL measures thickness badly, so keep the deviation at or below
**0.05 mm**. Save it next to the STEP file **with the same name**:

```
my_bracket.step
my_bracket.stl
```

### Assemblies

Export the assembly as **one STEP file** (Creo: Save a Copy on the `.asm`).
The components, their names and their positions all travel inside that single
file - there is no need to export the parts separately.

---

## Step 2 - Run the analysis

Two ways. They do exactly the same analysis.

### A. Command line - nothing to install

```bash
python analyze.py "C:\path\to\my_bracket.step" --process cnc_machining
```

Windows, without typing paths: drop your file's path onto `run_analysis.bat`,
or run:

```bat
run_analysis.bat "C:\path\to\my_bracket.step"
```

With the paired STL, so wall thickness is measured too:

```bash
python analyze.py my_bracket.step --mesh my_bracket.stl --process cnc_machining
```

Save the output:

```bash
python analyze.py my_bracket.step --mesh my_bracket.stl ^
    --process cnc_machining ^
    --output my_bracket_report.txt ^
    --html  my_bracket_report.html
```

(Use `\` instead of `^` for line continuation on macOS/Linux.)

### B. Web dashboard - upload and click

```bash
run_dashboard.bat            # Windows
.venv/bin/python web_dashboard/app.py    # macOS/Linux
```

Open <http://localhost:5000> and:

1. **Select CAD File** - your `.step` or `.stp` (or the assembly).
2. **Paired STL (optional)** - the matching `.stl`, if you exported one.
3. **Manufacturing Process** - see Step 3.
4. Fill in the assembly questions if you know them (Step 5).
5. Press **ANALYZE**.

The analysis runs on the server with a progress bar, then shows the scores,
rendered views of your part, the full report, and download buttons.

---

## Step 3 - Choose the process

This sets the limits the manufacturability checks use, so it changes the
findings. Pick the one you will actually make the part by:

| Process | Use when | Checks it turns on |
|---|---|---|
| `cnc_machining` | Milled or turned | Min hole 2.0 mm, min feature 1.0 mm, internal corner radii |
| `injection_molding` | Moulded plastic | Wall 1.5-5.0 mm, **draft angle**, fillets |
| `sheet_metal` | Folded sheet | Bend and hole ratios |
| `3d_printing` | Printed | Wall 1.0 mm, feature 0.5 mm |
| `general` | Not decided yet | Conservative defaults only |

For a moulded part, also say which way the tool pulls, if it is not Z:

```bash
python analyze.py housing.step --process injection_molding --pull Y
```

Draft is measured against that direction, so getting it wrong makes every
wall look undrafted.

---

## Step 4 - Read the report

The report has two kinds of content, and it labels which is which.

**Measured from your file** - bounding box, hole and boss diameters, face
counts, draft angle per face, and (with a paired STL) wall thickness, volume
and mass. These are facts read out of the geometry.

**Answered by you** - symmetry in the installed position, fastener count, tool
clearance, insertion motion. No single part file can tell anyone these, so
they come from the parameters you supply.

Findings are tagged:

| Tag | Meaning |
|---|---|
| `[FAIL]` | A violation. Fix before release. |
| `[CRIT]` | Critical inspection problem - the feature cannot be measured. |
| `[WARN]` | Worth a look; costs time or money, not feasibility. |
| `[INFO]` | A check that ran and **passed**, recorded so you know it ran. |
| `[NOTE]` | Something about the file itself, not the design. |

Read the `SUMMARY` block last: it lists the blocking findings under
**FIX FIRST**.

One rule worth knowing: **an empty findings list means "nothing found in the
checks that could be run"**, not "the part is fine". If the file carried no
measurable geometry the DFM and DFI scores come back as `n/a`, never as a
good score.

---

## Step 5 - Assemblies

Run an assembly exactly like a part:

```bash
python analyze.py my_assembly.step --process cnc_machining
```

The report gains a `COMPONENTS` block:

```
  Component                Envelope (mm)          Findings
  ----------------------------------------------------------------------
  top_cover                50.0 x 30.0 x 3.0      1 violation(s), 0 critical, 2 warning(s)
  base_plate               60.0 x 40.0 x 5.0      1 violation(s), 0 critical, 1 warning(s)
```

and every manufacturability and inspection finding names the component it
came from, so you know which part to fix. The component names are the ones
from your CAD assembly tree.

Serviceability stays at assembly level, because that is what you service. The
part count in the DFA score is read from the file, so you do not have to
count components yourself.

The bounding box is the **assembled** envelope, with each component's
position applied.

---

## Step 6 - Answer the assembly questions properly

The DFA and DFS scores are only as good as the answers you give. Copy the
template and edit it:

```bash
cp examples/dfx_params_template.json my_bracket_params.json
```

```json
{
  "dfa_parameters": {
    "num_fasteners": 4,
    "is_symmetric": false,
    "has_keying": true,
    "tool_clearance_mm": 18,
    "insertion_depth_mm": 30,
    "part_mass_g": 450
  },
  "dfm_parameters": { "process_type": "cnc_machining" },
  "density_g_cm3": 2.70
}
```

```bash
python analyze.py my_bracket.step --params my_bracket_params.json
```

Answer for the part **in its installed position**, not on the bench. A flag
on the command line beats the file, so you can reuse one parameter file
across processes:

```bash
python analyze.py my_bracket.step --params my_bracket_params.json --process 3d_printing
```

Set `density_g_cm3` to your material (steel 7.85, aluminium 2.70, ABS 1.05)
so the mass estimate is right.

---

## Step 7 - A whole folder at once

Put your exports in one folder and run:

```bash
python scripts/batch_analysis.py --input-dir ./exports --output-dir ./reports --process cnc_machining
```

You get one report per part, plus `batch_summary.csv` for Excel with every
part's scores and finding counts side by side. If a part is present as both
`part.step` and `part.stl`, the two are paired automatically and analysed as
one part.

---

## Step 8 - Get a PDF

Open the HTML report in any browser and print it: **Ctrl+P** > *Save as PDF*.
The page carries a print stylesheet, so the page furniture drops away. A PDF
holds the same information as the HTML report - there is no separate export
to install.

To keep the views as image files as well:

```bash
python analyze.py my_bracket.step --svg-dir views/
```

---

## Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| `Creo/NX part files are a closed vendor format` | You gave it a `.prt` / `.sldprt` | Export to STEP first (Step 1) |
| `Geometry: none measurable from this file` | The STEP export carried no solid | Re-export with **Solids** ticked, AP214 |
| `no solid model` note | Surfaces only | Same - export solids |
| DFM and DFI show `n/a` | Nothing could be measured, so nothing was checked | Fix the export; do not read this as a pass |
| `Paired mesh ... check the two files are the same model` | The STL is of a different part | Re-export the STL from the same model |
| Wall thickness missing | No STL supplied | Add `--mesh part.stl`, or upload it in the dashboard |
| Every wall reports 0 degrees draft | Correct for a machined part; for a moulded one, the pull direction is probably wrong | Set `--pull X`, `--pull Y` or `--pull Z` |
| `'pip' is not recognized` | Bare `pip` is not on PATH | Run `setup.bat`, or use `.venv\Scripts\python.exe -m pip` |
| Dashboard will not start | Flask is not installed in that interpreter | Run `setup.bat` / `./setup.sh`, then `run_dashboard.bat` |
| Port 5000 in use | Something else has it | `set DFX_PORT=5001` then start the dashboard |

---

## What it cannot do

Stated plainly so you do not read a clean report as more than it is:

* It cannot read `.prt`, `.sldprt`, `.asm`, `.iges` or `.fcstd`.
* Without a paired STL there is **no wall thickness figure at all**.
* Wall thickness is **sampled** by ray casting - it reports the thinnest wall
  found, not a proven global minimum.
* A cylindrical face may be a hole, a boss or an external round; the report
  says "cylindrical feature" rather than guessing.
* Undercuts and side actions are not detected.
* STEP wireframe views have no hidden-line removal. Supply the STL for solid
  shaded views.
