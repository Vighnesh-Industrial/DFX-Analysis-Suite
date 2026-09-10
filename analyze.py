#!/usr/bin/env python3
"""Command-line entry point for the DFX Analysis Suite.

Runs a full Design for Excellence study on a CAD file and prints the report.
This script needs nothing beyond the Python standard library - no Flask, no
virtual environment, no CAD software:

    python analyze.py example_parts/sample_bracket.STEP
    python analyze.py part.stl --process injection_molding --json out.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dfx_analyzers import ComprehensiveDFXAnalyzer
from dfx_analyzers.dfm_analyzer import DFMAnalyzer

PROCESSES = sorted(DFMAnalyzer().thresholds.keys()) + ['general']


def build_parser():
    parser = argparse.ArgumentParser(
        description='Run a DFX (Design for Excellence) study on a CAD file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Supported for measurement: STEP (.step/.stp) and STL (.stl).\n'
               'Creo, SolidWorks and IGES files must be exported to STEP first.')
    parser.add_argument('cad_file', help='Path to the CAD file to analyse')
    parser.add_argument('--process', default=None, choices=PROCESSES,
                        help='Manufacturing process for the DFM checks '
                             '(default: general, or whatever --params says)')
    parser.add_argument('--mesh', metavar='FILE',
                        help='A paired STL of the same model, to measure wall '
                             'thickness and true volume that a STEP file '
                             'cannot supply')
    parser.add_argument('--name', help='Component name for the report')
    parser.add_argument('--params', metavar='FILE',
                        help='JSON file of DFA/DFS parameters '
                             '(see examples/dfx_params_template.json)')
    parser.add_argument('--output', '-o', metavar='FILE',
                        help='Write the text report to this file')
    parser.add_argument('--json', metavar='FILE',
                        help='Write machine-readable results to this JSON file')
    parser.add_argument('--html', metavar='FILE',
                        help='Write a printable HTML report to this file')
    parser.add_argument('--pull', default='Z', choices=['X', 'Y', 'Z'],
                        help='Mould pull direction for the draft check (default Z)')
    parser.add_argument('--svg-dir', metavar='DIR',
                        help='Write each rendered view as an SVG file here')
    parser.add_argument('--no-views', action='store_true',
                        help='Skip rendering views (faster on dense meshes)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Do not print the report to the screen')
    return parser


def load_params(path):
    if not path:
        return {}
    with open(path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)
    # Accept both a flat parameter dict and the template's nested layout.
    params = dict(data.get('dfa_parameters', {}))
    dfm = data.get('dfm_parameters', {})
    if 'process_type' in dfm:
        params['process_type'] = dfm['process_type']
    for key, value in data.items():
        if key not in ('dfa_parameters', 'dfm_parameters', 'notes',
                       'component_name'):
            params[key] = value
    return params


def main(argv=None):
    args = build_parser().parse_args(argv)

    if not os.path.exists(args.cad_file):
        print("Error: file not found: %s" % args.cad_file, file=sys.stderr)
        return 2

    try:
        params = load_params(args.params)
    except (OSError, ValueError) as error:
        print("Error: could not read parameters file: %s" % error, file=sys.stderr)
        return 2

    # An explicit --process beats the parameters file; the file beats the
    # built-in default.
    process = args.process or params.get('process_type') or 'general'
    params['process_type'] = process

    if args.mesh and not os.path.exists(args.mesh):
        print("Error: paired mesh not found: %s" % args.mesh, file=sys.stderr)
        return 2

    pull = {'X': (1.0, 0.0, 0.0), 'Y': (0.0, 1.0, 0.0),
            'Z': (0.0, 0.0, 1.0)}[args.pull]

    def show_progress(fraction, message):
        if not args.quiet:
            sys.stderr.write('\r  %-58s %3d%%' % (message[:58], fraction * 100))
            sys.stderr.flush()

    analyzer = ComprehensiveDFXAnalyzer(
        args.cad_file, process_type=process, component_name=args.name,
        pull_direction=pull, progress=show_progress, mesh_path=args.mesh)
    if not args.quiet:
        sys.stderr.write('\r' + ' ' * 66 + '\r')
    report = analyzer.generate_master_report(params)

    if not args.quiet:
        # Never let a console that cannot render a character kill the run.
        sys.stdout.write(report.encode(
            sys.stdout.encoding or 'utf-8', errors='replace').decode(
            sys.stdout.encoding or 'utf-8', errors='replace'))
        sys.stdout.write('\n')

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as handle:
            handle.write(report)
        print("Report written to %s" % args.output)

    if args.html:
        with open(args.html, 'w', encoding='utf-8') as handle:
            handle.write(analyzer.to_html(params, include_views=not args.no_views))
        print("HTML report written to %s" % args.html)

    if args.svg_dir and not args.no_views:
        os.makedirs(args.svg_dir, exist_ok=True)
        written = 0
        for view in analyzer.views():
            path = os.path.join(args.svg_dir, '%s.svg' % view['name'])
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(view['svg'])
            written += 1
        if written:
            print("%d view(s) written to %s" % (written, args.svg_dir))
        else:
            print("No views to write: %s" % (analyzer.view_note() or 'none'))

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(analyzer.to_dict(params), handle, indent=2)
        print("JSON results written to %s" % args.json)

    if not analyzer.geometry.readable:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
