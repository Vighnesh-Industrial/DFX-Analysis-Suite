# Installation

## Requirements

* Python 3.8 or newer. Nothing else is required for the analysis itself.

Check what you have:

```bash
python --version      # Windows: py -3 --version
```

If Python is missing, install it from <https://www.python.org/downloads/> and
tick **"Add python.exe to PATH"** during installation.

---

## Option A - command line only (nothing to install)

The analysis core imports only the Python standard library.

```bash
git clone https://github.com/Vighnesh-Industrial/DFX-Analysis-Suite.git
cd DFX-Analysis-Suite
python analyze.py example_parts/sample_bracket.STEP
```

That is the whole installation. If this works, the suite is installed
correctly.

---

## Option B - with the web dashboard

The dashboard needs Flask, so it needs a virtual environment.

### Windows

Double-click **`setup.bat`**, or run it from a Command Prompt:

```bat
setup.bat
```

It creates `.venv`, installs the dependencies with `python -m pip`, and runs
the test suite to prove the install. Then:

```bat
run_dashboard.bat
```

### macOS / Linux

```bash
./setup.sh
.venv/bin/python web_dashboard/app.py
```

Open <http://localhost:5000>.

---

## Doing it by hand

If you prefer to run the commands yourself, always drive pip through the
interpreter you want to install into. This is what avoids the classic
"pip is not recognized" and "wrong interpreter" problems:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe web_dashboard\app.py
```

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python web_dashboard/app.py
```

You never have to run `activate`.

---

## Requirement files

| File | Contents | When you need it |
|---|---|---|
| `requirements.txt` | Flask, Flask-Cors, Werkzeug | Only for the web dashboard |
| `requirements_web.txt` | Includes `requirements.txt` | Kept for backwards compatibility |
| `requirements-dev.txt` | pytest, CadQuery | Running tests with pytest, or regenerating the sample parts |

**FreeCAD is not required and is not installable with pip.** Earlier versions
of this project listed `FreeCAD>=0.21.0` in `requirements.txt`, which made
every `pip install -r requirements.txt` fail before it reached Flask. The
geometry reader is now built in, so there is nothing external to install.

---

## Environment variables for the dashboard

| Variable | Default | Purpose |
|---|---|---|
| `DFX_HOST` | `127.0.0.1` | Set to `0.0.0.0` to expose the server on your network |
| `DFX_PORT` | `5000` | Change the port if 5000 is taken |
| `DFX_DEBUG` | `0` | Set to `1` for the Flask reloader while developing |

---

## Troubleshooting

**`pip is not recognized as an internal or external command`**
Use `.venv\Scripts\python.exe -m pip ...` instead of bare `pip`, or run
`setup.bat`.

**`ModuleNotFoundError: No module named 'flask'`**
The packages were installed into a different interpreter than the one running
the server. Start the server with `.venv\Scripts\python.exe web_dashboard\app.py`.

**`The system cannot find the path specified`**
Command Prompt is not in the project folder. Run `cd` to the folder that
contains `analyze.py`, or use the `.bat` files - they change directory
themselves.

**Port 5000 is already in use**
`set DFX_PORT=5001` on Windows, or `DFX_PORT=5001` on macOS/Linux.

**The report has no findings**
Check the `[NOTE]` lines under *MEASURED GEOMETRY*. A vendor format such as
`.prt` cannot be measured; export the model as STEP first.
