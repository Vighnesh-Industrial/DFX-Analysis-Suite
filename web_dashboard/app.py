"""Flask Web Dashboard for DFX Analysis Suite"""

import os
import sys
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dfx_analyzers import ComprehensiveDFXAnalyzer, DFAAnalyzer
from dfx_analyzers.cad_reader import READABLE_EXTENSIONS, RECOGNISED_EXTENSIONS
from jobs import JobStore

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

# Analysis runs on a worker thread so a dense mesh does not block the browser.
jobs = JobStore()


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


def run_analysis(job, filepath, filename, params, timestamp):
    """The background worker: read, analyse, render and write the reports."""
    job.report(0.05, 'Reading CAD file')

    analyzer = ComprehensiveDFXAnalyzer(
        filepath,
        process_type=params.get('process_type', 'general'),
        progress=lambda fraction, message: job.report(
            0.05 + 0.45 * fraction, message))

    job.report(0.55, 'Running DFX checks')
    master_report = analyzer.generate_master_report(params)

    job.report(0.72, 'Rendering views')
    views = analyzer.views()

    job.report(0.88, 'Writing reports')
    report_filename = 'DFX_Report_%s.txt' % timestamp
    # encoding is explicit: the default on Windows is cp1252, which cannot
    # encode every character a report may contain.
    with open(os.path.join(app.config['UPLOAD_FOLDER'], report_filename),
              'w', encoding='utf-8') as handle:
        handle.write(master_report)

    html_filename = 'DFX_Report_%s.html' % timestamp
    with open(os.path.join(app.config['UPLOAD_FOLDER'], html_filename),
              'w', encoding='utf-8') as handle:
        handle.write(analyzer.to_html(params))

    return {
        'success': True,
        'filename': filename,
        'report_filename': report_filename,
        'html_filename': html_filename,
        'report': master_report,
        'geometry': analyzer.geometry.to_dict(),
        'scores': analyzer.scores(),
        'components': analyzer.findings_by_component(),
        'views': views,
        'view_note': analyzer.view_note(),
        'timestamp': timestamp,
    }


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Accept a CAD file and queue it for analysis.

    Returns 202 with a job id; poll /api/jobs/<id> for progress and result.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    uploaded = request.files['file']
    if uploaded.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(uploaded.filename):
        return jsonify({'error': 'File type not allowed. Allowed: %s'
                                 % ', '.join(sorted(ALLOWED_EXTENSIONS))}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    filename = '%s_%s' % (timestamp, secure_filename(uploaded.filename))
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    uploaded.save(filepath)

    params = collect_params(request.form)
    job = jobs.submit(
        lambda job: run_analysis(job, filepath, filename, params, timestamp),
        label=secure_filename(uploaded.filename))

    return jsonify({'job_id': job.id,
                    'status': job.status,
                    'poll_url': '/api/jobs/%s' % job.id}), 202


@app.route('/api/jobs/<job_id>')
def job_status(job_id):
    """Progress and, once finished, the result of one analysis."""
    job = jobs.get(job_id)
    if job is None:
        return jsonify({'error': 'Unknown job id'}), 404
    return jsonify(job.to_dict())


@app.route('/api/jobs')
def job_list():
    """Recent jobs, without their results."""
    return jsonify({'jobs': [job.to_dict(include_result=False)
                             for job in jobs.recent(20)]})


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
