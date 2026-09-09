"""Helper for getting Creo (.prt/.asm) geometry into a format this tool can read.

Creo files are a closed format. Nothing outside PTC's own software can read
them, so this script does not pretend to convert them on its own: it looks for
an installed Creo and drives it if it finds one, and otherwise prints the exact
manual export steps.

    python scripts/convert_creo_to_step.py my_part.prt
    python scripts/convert_creo_to_step.py my_part.prt -o my_part.STEP
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Where Creo usually lands on Windows. Add your own path if it differs.
CREO_CANDIDATES = [
    r"C:\Program Files\PTC\Creo 10.0\Parametric\bin\parametric.exe",
    r"C:\Program Files\PTC\Creo 9.0\Parametric\bin\parametric.exe",
    r"C:\Program Files\PTC\Creo 8.0\Parametric\bin\parametric.exe",
    r"C:\Program Files\PTC\Creo 7.0\Parametric\bin\parametric.exe",
]

MANUAL_STEPS = """
Export the model to STEP from Creo itself:

  1. Open the .prt or .asm file in Creo Parametric.
  2. File > Save As > Save a Copy.
  3. Set 'Type' to  STEP (*.stp, *.step).
  4. In the export dialog choose AP214 (or AP203) and 'Solids'.
  5. Save, then analyse the exported file:

       python analyze.py my_part.stp

The same applies to SolidWorks (File > Save As > STEP) and to any other CAD
system: STEP AP203/AP214 is the interchange format this tool reads.
"""


def find_creo():
    """Return the path to an installed Creo executable, or None."""
    for candidate in CREO_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    return None


def convert_creo_to_step(input_file, output_file=None):
    """Try to export a Creo file to STEP.

    Returns True only if a STEP file was actually produced.
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print("Error: file '%s' not found" % input_file)
        return False

    if input_path.suffix.lower() not in ('.prt', '.asm'):
        print("Error: expected a .prt or .asm file, got '%s'" % input_path.suffix)
        return False

    output_path = Path(output_file) if output_file else input_path.with_suffix('.stp')

    creo = find_creo()
    if not creo:
        print("Creo was not found on this machine, so this file cannot be "
              "converted automatically.")
        print("Looked in:")
        for candidate in CREO_CANDIDATES:
            print("  %s" % candidate)
        print(MANUAL_STEPS)
        return False

    print("Found Creo: %s" % creo)
    print("Exporting %s -> %s" % (input_path, output_path))
    try:
        subprocess.run([creo, '-g:no_graphics', '-i', str(input_path),
                        '-o', str(output_path), '-t', 'step'],
                       check=True, timeout=600)
    except (subprocess.SubprocessError, OSError) as error:
        print("Creo export failed: %s" % error)
        print(MANUAL_STEPS)
        return False

    if not output_path.exists():
        print("Creo ran but produced no STEP file.")
        print(MANUAL_STEPS)
        return False

    print("OK: wrote %s" % output_path)
    print("Now run:  python analyze.py \"%s\"" % output_path)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Export a Creo .prt/.asm file to STEP so it can be analysed.')
    parser.add_argument('input_file', help='Path to the Creo file (.prt or .asm)')
    parser.add_argument('-o', '--output', help='Output STEP file path')
    args = parser.parse_args(argv)
    return 0 if convert_creo_to_step(args.input_file, args.output) else 1


if __name__ == '__main__':
    sys.exit(main())
