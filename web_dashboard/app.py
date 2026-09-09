"""Flask Web Dashboard for DFX Analysis Suite"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers import ComprehensiveDFXAnalyzer, DFAAnalyzer, DFMAnalyzer, DFIAnalyzer, DFSAnalyzer

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'step', 'stp', 'iges', 'igs', 'prt', 'asm', 'sldprt', 'sldasm', 'fcstd', 'stl'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/api/formats')
def get_formats():
    """Get supported CAD formats"""
    formats = {
        'STEP': {'.step', '.stp'},
        'IGES': {'.iges', '.igs'},
        'Creo Part': {'.prt'},
        'Creo Assembly': {'.asm'},
        'SolidWorks Part': {'.sldprt'},
        'SolidWorks Assembly': {'.sldasm'},
        'FreeCAD': {'.fcstd'},
        'STL/Mesh': {'.stl'}
    }
    return jsonify(formats)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Upload and analyze CAD file"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Get analysis parameters from form
        dfa_params = {
            'combined': request.form.get('combined', 'false').lower() == 'true',
            'num_parts': int(request.form.get('num_parts', 1)),
            'is_symmetric': request.form.get('is_symmetric', 'false').lower() == 'true',
            'has_guides': request.form.get('has_guides', 'false').lower() == 'true',
            'num_fasteners': int(request.form.get('num_fasteners', 0)),
            'use_snap_fit': request.form.get('use_snap_fit', 'false').lower() == 'true',
            'fasteners_standardized': request.form.get('fasteners_standardized', 'false').lower() == 'true',
            'has_grip_feature': request.form.get('has_grip_feature', 'false').lower() == 'true',
            'part_mass_g': float(request.form.get('part_mass_g', 500)),
            'fragile': request.form.get('fragile', 'false').lower() == 'true',
            'straight_line_insertion': request.form.get('straight_line_insertion', 'true').lower() == 'true',
            'rotation_needed': request.form.get('rotation_needed', 'false').lower() == 'true',
            'insertion_depth_mm': float(request.form.get('insertion_depth_mm', 0)),
            'tool_clearance_mm': float(request.form.get('tool_clearance_mm', 15)),
            'is_asymmetric': request.form.get('is_asymmetric', 'false').lower() == 'true',
            'has_keying': request.form.get('has_keying', 'false').lower() == 'true',
            'unique_features': request.form.get('unique_features', 'false').lower() == 'true'
        }
        
        # Run analysis
        analyzer = ComprehensiveDFXAnalyzer(filepath)
        master_report = analyzer.generate_master_report(dfa_params)
        
        # Save report
        report_filename = f"DFX_Report_{timestamp}.txt"
        report_filepath = os.path.join(app.config['UPLOAD_FOLDER'], report_filename)
        with open(report_filepath, 'w') as f:
            f.write(master_report)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'report_filename': report_filename,
            'report': master_report,
            'timestamp': timestamp
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-dfa', methods=['POST'])
def analyze_dfa():
    """Quick DFA Analysis"""
    try:
        data = request.get_json()
        component_name = data.get('component_name', 'Component')
        params = data.get('parameters', {})
        
        dfa = DFAAnalyzer(component_name)
        report = dfa.generate_dfa_report(**params)
        
        return jsonify({
            'success': True,
            'report': report,
            'scores': dfa.scores
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download(filename):
    """Download analysis report"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
