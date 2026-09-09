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
    parser.add_argument('--process', default='general', choices=PROCESSES,
                        help='Manufacturing process for the DFM checks')
    parser.add_argument('--name', help='Component name for the report')
    parser.add_argument('--params', metavar='FILE',
                        help='JSON file of DFA/DFS parameters '
                             '(see examples/dfx_params_template.json)')
    parser.add_argument('--output', '-o', metavar='FILE',
                        help='Write the text report to this file')
    parser.add_argument('--json', metavar='FILE',
                        help='Write machine-readable results to this JSON file')
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

    params.setdefault('process_type', args.process)

    analyzer = ComprehensiveDFXAnalyzer(
        args.cad_file, process_type=args.process, component_name=args.name)
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

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(analyzer.to_dict(params), handle, indent=2)
        print("JSON results written to %s" % args.json)

    if not analyzer.geometry.readable:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
