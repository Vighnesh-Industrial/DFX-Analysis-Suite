"""Batch analysis script for multiple CAD files"""

import argparse
import os
import json
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers import ComprehensiveDFXAnalyzer
from datetime import datetime

def batch_analyze(input_dir, output_dir=None, process_type='general', **dfa_params):
    """
    Analyze multiple CAD files in a directory.
    
    Args:
        input_dir (str): Directory containing CAD files
        output_dir (str): Output directory for reports
        process_type (str): Manufacturing process type
        **dfa_params: DFA parameters
    """
    
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print(f"❌ Error: Directory '{input_dir}' not found")
        return
    
    if output_dir is None:
        output_dir = 'dfx_reports'
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Find all CAD files
    supported_formats = {'.step', '.stp', '.iges', '.igs', '.prt', '.asm', '.sldprt', '.sldasm', '.fcstd', '.stl'}
    cad_files = []
    
    for file in input_path.iterdir():
        if file.suffix.lower() in supported_formats:
            cad_files.append(file)
    
    if not cad_files:
        print(f"❌ No CAD files found in {input_dir}")
        return
    
    print(f"\n🏭 DFX BATCH ANALYSIS")
    print(f"Found {len(cad_files)} CAD files")
    print(f"Output directory: {output_path}\n")
    
    results_summary = []
    
    for idx, cad_file in enumerate(cad_files, 1):
        print(f"[{idx}/{len(cad_files)}] Analyzing: {cad_file.name}")
        
        try:
            analyzer = ComprehensiveDFXAnalyzer(str(cad_file))
            report = analyzer.generate_master_report(dfa_params)
            
            # Save report
            report_filename = output_path / f"{cad_file.stem}_DFX_Report.txt"
            with open(report_filename, 'w') as f:
                f.write(report)
            
            print(f"  ✅ Report saved: {report_filename.name}")
            
            results_summary.append({
                'file': cad_file.name,
                'report': str(report_filename),
                'status': 'SUCCESS'
            })
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            results_summary.append({
                'file': cad_file.name,
                'error': str(e),
                'status': 'FAILED'
            })
    
    # Save summary
    summary_file = output_path / 'batch_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    print(f"\n✅ Batch analysis complete!")
    print(f"Summary saved: {summary_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch analyze CAD files')
    parser.add_argument('--input-dir', required=True, help='Input directory with CAD files')
    parser.add_argument('--output-dir', help='Output directory for reports')
    parser.add_argument('--process', default='general', help='Manufacturing process type')
    
    args = parser.parse_args()
    
    batch_analyze(
        args.input_dir,
        args.output_dir,
        args.process
    )
