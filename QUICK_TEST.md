# Quick Test

Three ways to confirm the suite works, fastest first.

## 1. Analyse the sample part (no installation at all)

```bash
python analyze.py example_parts/sample_bracket.STEP --process cnc_machining
```

Windows: double-click **`run_analysis.bat`**.

You should see the geometry read out of the file:

```
  Bounding box:    80.00 x 63.00 x 25.00 mm
  B-rep faces:     23 (planar: 12)
  Solid bodies:    1
  Cylindrical:     11 faces; diameters 1.50, 6.50, 10.00, 16.00, 20.00 mm
```

and these findings, which are real properties of the sample bracket:

* **DFM violation** - the 1.50 mm pilot hole is below the 2.00 mm CNC minimum.
* **DFI critical** - that same hole is too small for a 5 mm CMM touch probe.
* **DFM warning** - five distinct diameters means five tool changes.

Then try the two other fixtures, which exercise the other measurements:

```bash
# A moulded housing with a real 2 degree taper - draft is measured, not guessed
python analyze.py example_parts/sample_housing.STEP --process injection_molding

# The same bracket as a mesh - wall thickness is measured by ray casting
python analyze.py example_parts/sample_bracket.stl --process injection_molding

# A three-part assembly - findings name the component they came from
python analyze.py example_parts/sample_assembly.STEP

# STEP features plus mesh wall thickness, in one report
python analyze.py example_parts/sample_bracket.STEP --mesh example_parts/sample_bracket.stl
```

The housing reports `Draft confirmed - all 8 wall faces carry between 2.0 and
2.0 degrees of draft`; run the bracket through the same process and it fails
the draft check with `9 of 9 wall faces at 0.0 deg`.

### Views of the part

```bash
python analyze.py example_parts/sample_bracket.STEP --svg-dir views/
```

Writes `iso.svg`, `front.svg`, `top.svg` and `right.svg`. STEP files render as
wireframes with proper arcs for holes and fillets; STL files render shaded.

### A printable report

```bash
python analyze.py example_parts/sample_bracket.STEP --html report.html
```

Open `report.html` in any browser and print it to PDF (**Ctrl+P**, then
*Save as PDF*) - it carries a print stylesheet for exactly that. The dashboard offers
the same file under **Download Printable Report**.

If the geometry block says *"none measurable"*, the file you passed has no
solid model in it.

## 2. Run the tests

```bash
python -m unittest discover -s tests
```

Expect `OK` for 96 tests (17 skip if Flask is not installed).

## 3. Start the web dashboard

```bash
# once
./setup.sh                 # Windows: setup.bat

# then
.venv/bin/python web_dashboard/app.py     # Windows: run_dashboard.bat
```

Open <http://localhost:5000>, choose a process, upload
`example_parts/sample_bracket.STEP` and press **ANALYZE**.

The analysis runs in the background: you should see a progress bar move
through *Reading CAD file*, *Measuring wall thickness*, *Running DFX checks*
and *Rendering views*. The result shows four rendered views of the part above
the report.

---

Working with your own CAD? See [docs/WORKFLOW.md](docs/WORKFLOW.md) for the
export settings and the full step-by-step.

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `'pip' is not recognized` | The virtual environment is not on PATH | Never call bare `pip`. Use `.venv\Scripts\python.exe -m pip ...`, or just run `setup.bat`, which does this for you |
| `ModuleNotFoundError: No module named 'flask'` | Dependencies went into a different interpreter | Run `setup.bat` / `./setup.sh`, then start the server with the venv's own python |
| `The system cannot find the path specified` | Command Prompt is not in the project folder | `cd` into the folder containing `analyze.py`, or use the `.bat` files, which `cd` themselves |
| `'charmap' codec can't encode character` | Fixed. Reports are ASCII and all files are written as UTF-8 | Pull the latest code |
| Report has no findings | The file carried no solid geometry, or it is a vendor format | Read the `[NOTE]` lines in the report; export as STEP AP203/AP214 |
