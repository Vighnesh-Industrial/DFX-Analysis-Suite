# Project Status

Written 2026-09-09, when the project moved from the GitHub Copilot thread
"Design for excellence study of CAD" into Claude Code.

## Where the project stood

The Copilot thread created this repository and pushed the module skeleton, the
Flask dashboard, docs and tests. It then spent its last dozen exchanges trying
to get the dashboard to start on Windows, cycling through `pip is not
recognized`, `ModuleNotFoundError: No module named 'Flask'` and a `charmap`
codec error. None of them were fixed, and the analysis had never been run on a
real CAD file.

## What was actually wrong

Three defects, none of which were visible from the error messages being chased:

1. **`requirements.txt` could not install.** It pinned `FreeCAD>=0.21.0`, which
   is not on PyPI at all, plus `steptools`, `pyassimp` and `openpyxl>=3.10.0`
   (a version that does not exist). `requirements_web.txt` began with
   `-r requirements.txt`, so every install attempt failed before it ever
   reached Flask. That is why Flask was never installed, which is why the
   server would not start.

2. **The `charmap` crash was in `app.py`, not the templates.** The app wrote
   reports with `open(path, 'w')` - cp1252 on Windows - while the reports
   contained box-drawing characters and emoji. Removing emoji from the HTML
   could never have fixed it.

3. **The analyzers never opened the CAD file.** `ComprehensiveDFXAnalyzer`
   took a file path and stored it. DFM, DFI and DFS only reported findings
   that had been added by hand, so every upload returned an empty report
   regardless of the part. The tool looked like it worked and measured
   nothing.

Smaller defects found while fixing those: `static/js/main.js` opened with a
Python docstring (a JavaScript syntax error, so the file never ran), every
checkbox in the dashboard was ignored because the code compared against
`'true'` while HTML posts `'on'`, an empty number field returned HTTP 500, the
referenced `static/css/style.css` did not exist, the batch script overwrote a
report when two files shared a stem, and the Creo converter called a
`pro_engineer` module that does not exist.

## What the project does now

* **Reads CAD files.** `dfx_analyzers/cad_reader.py` parses STEP (ISO 10303-21)
  and STL with no third-party dependencies: bounding box, units, product name,
  face and solid counts, cylindrical/conical/toroidal radii, and for meshes the
  exact volume, surface area and watertightness. Validated against
  OpenCASCADE - identical face counts and radii on the sample part, STL volume
  within 0.01% of exact.
* **Runs real checks.** DFM and DFI findings are derived from those
  measurements. The sample bracket produces a genuine violation (a 1.5 mm hole
  below the 2.0 mm CNC minimum) and a genuine critical inspection finding (that
  hole cannot take a 5 mm CMM probe).
* **Installs.** `requirements.txt` is Flask plus two Flask dependencies. The
  analysis core needs nothing at all.
* **Runs on Windows.** `setup.bat`, `run_analysis.bat` and `run_dashboard.bat`
  drive `python -m pip` and the venv's own interpreter directly, never `pip`
  or `activate`. Reports are ASCII and all writes are explicitly UTF-8.
* **Is tested.** 53 tests, including regression tests for the cp1252 crash and
  the checkbox parsing.

## Deliberate limits

The tool reports what it can measure and says when it cannot measure something.
It does **not**:

* measure true wall thickness (needs a solid-modelling kernel);
* measure draft angle against a stated pull direction - it can only tell you
  whether conical faces exist at all;
* read `.prt`, `.asm`, `.sldprt`, `.sldasm`, `.iges` or `.fcstd`. These are
  accepted by the uploader, and produce a report telling you to export STEP.

A cylindrical face may be a hole, a boss or an external corner round; STEP does
not distinguish them without full topology traversal, so they are reported as
"cylindrical features" and never claimed to be holes.

## Sensible next steps

1. Distinguish holes from bosses and rounds by traversing face orientation in
   the B-rep, so the DFM messages can be more specific.
2. Measure draft angle from `CONICAL_SURFACE` half-angles against a pull
   direction the user picks.
3. Assembly-level DFA: read `NEXT_ASSEMBLY_USAGE_OCCURRENCE` from a STEP
   assembly to get a real part count instead of asking for it.
4. PDF export, which the original README promised and no code ever provided.
