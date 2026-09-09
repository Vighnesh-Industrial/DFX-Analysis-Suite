"""Flask Web Dashboard for DFX Analysis Suite"""

import os
import sys
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dfx_analyzers import ComprehensiveDFXAnalyzer, DFAAnalyzer
from dfx_analyzers.cad_reader import READABLE_EXTENSIONS, RECOGNISED_EXTENSIONS

app = Flask(__name__)
CORS(app)

# Absolute, so the server behaves the same whether it is started from the
# repository root or from inside web_dashboard/.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {ext.lstrip('.') for ext in RECOGNISED_EXTENSIONS}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

FALSE_VALUES = {'false', 'off', '0', 'no', 'n'}


def allowed_file(filename):
    return ('.' in filename
            and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS)


def form_flag(form, name):
    """Read a checkbox.

    An unchecked HTML checkbox is simply absent from the form, and a checked
    one posts the value "on" - not "true".  Absence therefore means False.
    An API client may also post an explicit "true"/"false" string.
    """
    if name not in form:
        return False
    return str(form.get(name, '')).strip().lower() not in FALSE_VALUES


def form_number(form, name, default, cast=float):
    raw = form.get(name, '')
    if raw is None or str(raw).strip() == '':
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return default


def collect_params(form):
    """Build the analysis parameters from the submitted form."""
    return {
        'process_type': form.get('process_type', 'general'),
        'combined': form_flag(form, 'combined'),
        'num_parts': form_number(form, 'num_parts', 1, int),
        'is_symmetric': form_flag(form, 'is_symmetric'),
        'has_guides': form_flag(form, 'has_guides'),
        'num_fasteners': form_number(form, 'num_fasteners', 0, int),
        'use_snap_fit': form_flag(form, 'use_snap_fit'),
        'fasteners_standardized': form_flag(form, 'fasteners_standardized'),
        'has_grip_feature': form_flag(form, 'has_grip_feature'),
        'part_mass_g': form_number(form, 'part_mass_g', 500.0),
        'fragile': form_flag(form, 'fragile'),
        'straight_line_insertion': form_flag(form, 'straight_line_insertion'),
        'rotation_needed': form_flag(form, 'rotation_needed'),
        'insertion_depth_mm': form_number(form, 'insertion_depth_mm', 0.0),
        'tool_clearance_mm': form_number(form, 'tool_clearance_mm', 15.0),
        'is_asymmetric': form_flag(form, 'is_asymmetric'),
        'has_keying': form_flag(form, 'has_keying'),
        'unique_features': form_flag(form, 'unique_features'),
        'density_g_cm3': form_number(form, 'density_g_cm3', 7.85),
    }


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/api/formats')
def get_formats():
    """Get supported CAD formats, and say which can actually be measured."""
    formats = []
    for extension, label in sorted(RECOGNISED_EXTENSIONS.items()):
        formats.append({
            'extension': extension,
            'format': label,
            'measurable': extension in READABLE_EXTENSIONS,
        })
    return jsonify({'formats': formats,
                    'measurable_extensions': sorted(READABLE_EXTENSIONS)})


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Upload and analyze CAD file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        uploaded = request.files['file']
        if uploaded.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(uploaded.filename):
            return jsonify({'error': 'File type not allowed. Allowed: %s'
                                     % ', '.join(sorted(ALLOWED_EXTENSIONS))}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = '%s_%s' % (timestamp, secure_filename(uploaded.filename))
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        uploaded.save(filepath)

        params = collect_params(request.form)
        analyzer = ComprehensiveDFXAnalyzer(
            filepath, process_type=params.get('process_type', 'general'))
        master_report = analyzer.generate_master_report(params)

        report_filename = 'DFX_Report_%s.txt' % timestamp
        report_filepath = os.path.join(app.config['UPLOAD_FOLDER'], report_filename)
        # encoding is explicit: the default on Windows is cp1252, which
        # cannot encode every character a report may contain.
        with open(report_filepath, 'w', encoding='utf-8') as handle:
            handle.write(master_report)

        return jsonify({
            'success': True,
            'filename': filename,
            'report_filename': report_filename,
            'report': master_report,
            'geometry': analyzer.geometry.to_dict(),
            'scores': analyzer.scores(),
            'timestamp': timestamp,
        })

    except Exception as error:  # noqa: BLE001 - surfaced to the user as JSON
        app.logger.exception('Analysis failed')
        return jsonify({'error': '%s: %s' % (type(error).__name__, error)}), 500


@app.route('/api/analyze-dfa', methods=['POST'])
def analyze_dfa():
    """Quick DFA Analysis"""
    try:
        data = request.get_json(silent=True) or {}
        dfa = DFAAnalyzer(data.get('component_name', 'Component'))
        report = dfa.generate_dfa_report(**data.get('parameters', {}))
        return jsonify({'success': True, 'report': report, 'scores': dfa.scores})
    except Exception as error:  # noqa: BLE001
        return jsonify({'error': '%s: %s' % (type(error).__name__, error)}), 500


@app.route('/api/download/<filename>')
def download(filename):
    """Download analysis report"""
    safe_name = secure_filename(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    if not os.path.isfile(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True)


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.1.0',
        'timestamp': datetime.now().isoformat(),
    })


@app.errorhandler(413)
def too_large(_error):
    return jsonify({'error': 'File is larger than the %d MB limit.'
                             % (MAX_FILE_SIZE // (1024 * 1024))}), 413


if __name__ == '__main__':
    # Binds to localhost by default. Set DFX_HOST=0.0.0.0 to expose it on the
    # network, and DFX_DEBUG=1 for the reloader while developing.
    host = os.environ.get('DFX_HOST', '127.0.0.1')
    port = int(os.environ.get('DFX_PORT', '5000'))
    debug = os.environ.get('DFX_DEBUG', '0') == '1'
    print('DFX Analysis Suite dashboard: http://%s:%d'
          % ('localhost' if host == '127.0.0.1' else host, port))
    app.run(debug=debug, host=host, port=port)
