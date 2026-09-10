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

## Second pass: closing the analysis gaps

The first pass made the tool install, run and actually read CAD files. The
second pass replaced the remaining proxies with real measurements:

* **Draft angle** is now measured per face, by resolving each face's surface
  normal out of the STEP file and comparing it to a pull direction you choose.
  The previous check assumed "no conical faces means no draft", which is wrong
  for prismatic parts: tapering a box produces slanted planes, not cones.
  Validated on a housing modelled with an exact 2 degree taper - the tool
  reports 2.0 degrees on all 8 wall faces, and 0.0 on the machined bracket.

* **Wall thickness** is measured by casting rays from face centres along the
  inward normal. Validated exactly: a 10 mm cube measures 9.999999 mm. This is
  the check DFM most needed, and it caught a genuine defect in the sample part
  while being written - the upstand bore had been cut from inside the wall,
  leaving a 3 mm blind pocket floor instead of a through hole.

* **Assembly part count** is read from the STEP assembly structure
  (NEXT_ASSEMBLY_USAGE_OCCURRENCE), so the DFA part-reduction score no longer
  depends on the user guessing. The bounding box still does not apply
  component placement transforms, and the report says so.

* **Bounding box accuracy.** It was computed from every CARTESIAN_POINT,
  including surface placement origins that can lie outside the solid - which
  overstated the bracket by 7 mm once the through bore was added. It now uses
  VERTEX_POINTs only, and matches the authored size exactly.

* **A printable HTML report**, self-contained and with no dependencies, so a
  study can be handed to someone or printed to PDF.

* **Checks that run and pass** are recorded as notes rather than warnings, so
  passing a check no longer costs score.

## Third pass: background jobs and views

* **The dashboard is asynchronous.** `POST /api/analyze` queues the work and
  returns a job id; the page polls for progress and shows a live bar through
  reading, thickness measurement, checks and rendering. Wall-thickness ray
  casting is the slow step, and it no longer risks a request timeout.
  Jobs run on worker threads and live in memory - right for a local tool,
  not for a shared deployment.

* **Rendered views of the part**, drawn without a third-party renderer:
  meshes are back-face culled, depth sorted and flat shaded with a
  camera-fixed light; STEP files are drawn from their own edge curves, with
  circles swept from centre, axis and sense flag so holes and fillets render
  as arcs rather than chords. This needed following the
  EDGE_CURVE -> SURFACE_CURVE -> CIRCLE indirection; drawing the chord instead
  had collapsed every hole to a dot and every fillet to a chamfer.

* **A file with no measurable geometry now scores n/a**, not 9/10. It had been
  scoring well precisely because none of the geometry checks could run, which
  is the failure mode this project exists to avoid.

## Fourth pass: assemblies, and main

* **Component placements are applied.** A STEP assembly keeps each component's
  geometry in its own coordinate system, and records the placement separately.
  Reading the geometry without that chain piled every component on the origin:
  the sample assembly's 28 mm stack measured 5 mm and the views drew the parts
  overlapping. The reader now follows
  `REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION` ->
  `ITEM_DEFINED_TRANSFORMATION`, resolves each component's world transform and
  applies it to both vertices and edges. Validated against the kernel on a
  three-part sample with a rotated component: 60 x 40 x 28 mm, exactly.

* **The work reached `main`.** Everything above had been sitting on a branch,
  so anyone cloning the repository still got the original broken code. The
  branch was merged into `main` on request.

## Fifth pass: per-component findings

An assembly was analysed as a single body, so a finding named the assembly
and gave no clue which component to fix. Components are now measured
separately - the reader attributes every geometry entity to the component
whose shape representation reaches it, and recovers each component's name by
walking back to its PRODUCT - and the manufacturability and inspection checks
run per component. Serviceability stays assembly-level, because a component
is what you make and an assembly is what you service.

The DFM and DFI scores became the mean across components rather than a single
running deduction: otherwise a ten-part assembly scored worse than a five-part
one simply for having more parts to find things in.

On the question of PDF: a PDF would carry exactly the same content as the
HTML report. It is a container, not another source of data, and the HTML
report already prints to PDF from any browser. No PDF exporter was added.

## Deliberate limits

The tool reports what it can measure and says when it cannot measure something.
It does **not**:

* measure wall thickness directly from a STEP B-rep - export an STL alongside
  and it is measured from that;
* tell a hole from a boss or an external corner round;
* apply assembly placement transforms to the bounding box;
* detect undercuts or side actions on a moulded part;
* read `.prt`, `.asm`, `.sldprt`, `.sldasm`, `.iges` or `.fcstd`. These are
  accepted by the uploader, and produce a report telling you to export STEP.

A cylindrical face may be a hole, a boss or an external corner round; STEP does
not distinguish them without full topology traversal, so they are reported as
"cylindrical features" and never claimed to be holes.

## Sensible next steps

1. Distinguish holes from bosses and rounds by traversing face orientation in
   the B-rep, so the DFM messages can be more specific.
2. Hidden-line removal for the STEP wireframe views.
3. Undercut detection for moulded parts, now that face normals and a pull
   direction are both available.
4. Wall thickness from a STEP B-rep directly, rather than via an STL export.
