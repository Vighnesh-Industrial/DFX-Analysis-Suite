# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

A Design for Excellence (DFX) analysis tool for CAD parts. It reads a CAD file,
measures what it can, and reports manufacturability (DFM), inspection (DFI),
assembly (DFA) and serviceability (DFS) findings.

## The rule that matters most

**Never invent a measurement.** Every number in a report must either be read
from the CAD file or supplied by the user. When something cannot be measured,
the code returns `None` and the report says so - it does not substitute a
default and present it as a finding. `CADGeometry.estimated_mass_g()` returning
`None` rather than a bounding-box guess is the reference example.

A related rule: an empty findings list means "nothing found in the checks that
could be run", and the reports say exactly that. Do not let a report imply a
part passed checks that never executed.

## Dependency policy

`dfx_analyzers/` and `analyze.py` import **standard library only**. This is
deliberate: the project's history is a user who could not get past
`pip install`, and the analysis has to work on a bare Python install.

* Flask, Flask-Cors and Werkzeug are for `web_dashboard/` only.
* CadQuery is dev-only, used by `scripts/generate_sample_parts.py`.
* Do not add a runtime dependency to the core without a strong reason. In
  particular `FreeCAD` is **not** pip-installable and must never reappear in
  `requirements.txt`.

## Windows encoding

Report text is plain ASCII on purpose, and every `open(..., 'w')` passes
`encoding='utf-8'` explicitly. Windows defaults to cp1252, and box-drawing
characters or emoji in a report crash the write with a `charmap` error. Tests
in `tests/test_reports.py` assert `report.encode('cp1252')` succeeds - keep
them passing rather than working around them.

## Layout

```
analyze.py                 CLI entry point, no dependencies
dfx_analyzers/
  cad_reader.py            STEP + STL parsing -> CADGeometry
  render.py                Orthographic SVG views (shaded mesh / STEP wireframe)
  html_report.py           Printable HTML report
  dfm_analyzer.py          Manufacturability checks (geometry-driven)
  dfi_analyzer.py          Inspection checks (geometry-driven)
  dfa_analyzer.py          Assembly scoring (parameter-driven)
  dfs_analyzer.py          Serviceability scoring
  master_analyzer.py       Orchestration, report assembly, scores()
web_dashboard/app.py       Flask dashboard; queues analyses as background jobs
web_dashboard/jobs.py      Thread-backed job runner with progress reporting
scripts/                   Batch analysis, Creo export helper, sample generator
example_parts/             sample_bracket.STEP and .stl (committed)
tests/                     96 tests
```

## Commands

```bash
python analyze.py example_parts/sample_bracket.STEP --process cnc_machining
python -m unittest discover -s tests          # no dependencies needed
.venv/bin/python -m pytest tests/ -q          # 96 pass
.venv/bin/python web_dashboard/app.py         # dashboard on :5000
```

## Testing conventions

* The web tests skip automatically when Flask is missing - keep that guard.
* `example_parts/sample_bracket.STEP` is a fixture with **deliberate** DFX
  problems (a 1.5 mm hole, five distinct diameters). Tests assert on those
  values, so regenerating the samples means updating the expectations in
  `tests/test_cad_reader.py`.
* The sample geometry was validated against the OpenCASCADE kernel: 23 faces,
  12 planes, 11 cylindrical radii, and an STL volume within 0.01% of exact.
* `sample_housing.STEP` has an exact 2 degree taper and `sample_assembly.STEP`
  has exactly 2 components. Tests assert those numbers.

## Measurement invariants worth protecting

* **Bounding box comes from VERTEX_POINTs only.** A CARTESIAN_POINT can be a
  surface placement origin sitting outside the solid; including those once
  overstated the bracket by 7 mm.
* **Draft is measured from face normals, not from the presence of cones.**
  Tapering a prismatic part produces slanted planes, so counting
  CONICAL_SURFACE entities misses most real draft.
* **Wall thickness is sampled, not exhaustive.** `measure_wall_thickness`
  casts rays from a subset of faces, so it reports the thinnest wall found.
  Never describe it as a proven global minimum.
* **A check that runs and passes is a note, not a warning.** Notes carry no
  score penalty; putting a pass in `warnings` silently costs the part 0.4.
* **No measurable geometry means no DFM/DFI score.** `scores()` returns `None`
  for both, not 10 minus a couple of warnings - otherwise an empty file reads
  as a good part. `geometry_measured` in the same dict says which it was.
* **Views are never faked.** `render_views` returns only the views the file
  can actually supply; `render_note` explains any absence.

## The dashboard is asynchronous

`POST /api/analyze` returns **202** with a `job_id`; the browser polls
`/api/jobs/<id>` for `status`, `progress` and `message`. Analysis runs on a
worker thread in `web_dashboard/jobs.py`. Tests must poll rather than expect a
result from the POST - see `_await_job` in `tests/test_web_app.py`.

## Adding a DFX check

1. Add the measurement to `cad_reader.py` if it is not already extracted.
2. Add the check as a `_check_*` method on the relevant analyzer, called from
   `analyze_geometry()`.
3. Guard it: return early when the measurement is `None`.
4. Write the recommendation as an action an engineer can take, with the number
   that triggered it.
5. Add a test that asserts the check fires on the sample bracket, or on a
   fixture built in the test.
