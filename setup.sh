#!/usr/bin/env bash
# DFX Analysis Suite - one-time setup for macOS and Linux.
set -euo pipefail
cd "$(dirname "$0")"

echo "=== DFX Analysis Suite setup ==="
PYTHON=${PYTHON:-python3}
"$PYTHON" --version

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating virtual environment in .venv ..."
    "$PYTHON" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Running the test suite ..."
.venv/bin/python -m unittest discover -s tests

cat <<'MSG'

=== Setup complete ===

  Analyse the sample part:   python3 analyze.py example_parts/sample_bracket.STEP
  Start the web dashboard:   .venv/bin/python web_dashboard/app.py
MSG
