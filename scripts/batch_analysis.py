"""Batch analysis script for multiple CAD files.

    python scripts/batch_analysis.py --input-dir example_parts --process cnc_machining

Needs nothing beyond the Python standard library.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers import ComprehensiveDFXAnalyzer
from dfx_analyzers.cad_reader import RECOGNISED_EXTENSIONS

SUPPORTED_FORMATS = set(RECOGNISED_EXTENSIONS)


def batch_analyze(input_dir, output_dir=None, process_type='general', **dfa_params):
    """Analyze every CAD file in a directory and write one report each.

    Returns the list of per-file result dictionaries.
    """
    input_path = Path(input_dir)
    if not input_path.is_dir():
        print("Error: directory '%s' not found" % input_dir)
        return []

    output_path = Path(output_dir or 'dfx_reports')
    output_path.mkdir(parents=True, exist_ok=True)

    found = sorted(f for f in input_path.iterdir()
                   if f.suffix.lower() in SUPPORTED_FORMATS)
    if not found:
        print("No CAD files found in %s" % input_dir)
        return []

    # A part exported as both STEP and STL is one part, not two: analyse the
    # B-rep and hand it the mesh, so features and wall thickness land in the
    # same report.
    meshes = {f.stem.lower(): f for f in found if f.suffix.lower() == '.stl'}
    cad_files = [f for f in found if f.suffix.lower() != '.stl']
    paired = {}
    for cad_file in cad_files:
        mesh = meshes.pop(cad_file.stem.lower(), None)
        if mesh is not None:
            paired[cad_file] = mesh
    # Any mesh with no B-rep partner is still a part in its own right.
    cad_files.extend(meshes.values())
    cad_files.sort()

    print("DFX BATCH ANALYSIS")
    print("Found %d CAD file(s); process: %s" % (len(cad_files), process_type))
    print("Output directory: %s\n" % output_path)

    results_summary = []
    for index, cad_file in enumerate(cad_files, 1):
        print("[%d/%d] Analyzing: %s" % (index, len(cad_files), cad_file.name))
        mesh = paired.get(cad_file)
        if mesh is not None:
            print("      paired with %s for wall thickness" % mesh.name)
        try:
            analyzer = ComprehensiveDFXAnalyzer(
                str(cad_file), process_type=process_type,
                mesh_path=str(mesh) if mesh is not None else None)
            report = analyzer.generate_master_report(dict(dfa_params))
            scores = analyzer.scores()

            # Include the suffix: part.STEP and part.stl must not
            # write to the same report file.
            report_file = output_path / ('%s_%s_DFX_Report.txt'
                                         % (cad_file.stem,
                                            cad_file.suffix.lstrip('.').lower()))
            # Explicit encoding: the Windows default (cp1252) cannot encode
            # every character a report may contain.
            with open(report_file, 'w', encoding='utf-8') as handle:
                handle.write(report)

            print("      OK  composite %.1f/10, %d violation(s), %d critical  -> %s"
                  % (scores['composite'] or 0, scores['dfm_violations'],
                     scores['dfi_critical'], report_file.name))

            results_summary.append({
                'file': cad_file.name,
                'status': 'SUCCESS',
                'report': str(report_file),
                'composite': scores['composite'],
                'dfa': scores['dfa'], 'dfm': scores['dfm'],
                'dfi': scores['dfi'], 'dfs': scores['dfs'],
                'dfm_violations': scores['dfm_violations'],
                'dfi_critical': scores['dfi_critical'],
                'readable': analyzer.geometry.readable,
                'paired_mesh': mesh.name if mesh is not None else '',
            })
        except Exception as error:  # noqa: BLE001 - one bad file must not stop the batch
            print("      FAILED: %s: %s" % (type(error).__name__, error))
            results_summary.append({'file': cad_file.name, 'status': 'FAILED',
                                    'error': str(error)})

    summary_json = output_path / 'batch_summary.json'
    with open(summary_json, 'w', encoding='utf-8') as handle:
        json.dump(results_summary, handle, indent=2)

    summary_csv = output_path / 'batch_summary.csv'
    columns = ['file', 'status', 'composite', 'dfa', 'dfm', 'dfi', 'dfs',
               'dfm_violations', 'dfi_critical', 'readable', 'paired_mesh',
               'report', 'error']
    with open(summary_csv, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results_summary)

    print("\nBatch analysis complete.")
    print("Summary: %s and %s" % (summary_json.name, summary_csv.name))
    return results_summary


def main(argv=None):
    parser = argparse.ArgumentParser(description='Batch analyze CAD files')
    parser.add_argument('--input-dir', required=True, help='Directory of CAD files')
    parser.add_argument('--output-dir', help='Where to write reports')
    parser.add_argument('--process', default='general',
                        help='Manufacturing process for the DFM checks')
    parser.add_argument('--params', help='JSON file of DFA/DFS parameters')
    args = parser.parse_args(argv)

    params = {}
    if args.params:
        with open(args.params, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        params = dict(data.get('dfa_parameters', data))

    results = batch_analyze(args.input_dir, args.output_dir, args.process, **params)
    return 0 if results else 1


if __name__ == '__main__':
    sys.exit(main())
