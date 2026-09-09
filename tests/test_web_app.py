"""Tests for the Flask dashboard.

Skipped automatically when Flask is not installed, so the core test suite
still runs on a bare Python install.
"""

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from web_dashboard.app import app, form_flag, form_number
    FLASK_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the environment
    FLASK_AVAILABLE = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_STEP = os.path.join(ROOT, 'example_parts', 'sample_bracket.STEP')


@unittest.skipUnless(FLASK_AVAILABLE, 'Flask is not installed')
class TestFormParsing(unittest.TestCase):
    """Regression: an HTML checkbox posts "on", never "true", so the old
    `== 'true'` comparison made every boolean parameter silently False."""

    def test_checked_box_posts_on(self):
        self.assertTrue(form_flag({'is_symmetric': 'on'}, 'is_symmetric'))

    def test_unchecked_box_is_absent(self):
        self.assertFalse(form_flag({}, 'is_symmetric'))

    def test_explicit_false_from_an_api_client(self):
        self.assertFalse(form_flag({'is_symmetric': 'false'}, 'is_symmetric'))

    def test_blank_number_field_uses_the_default(self):
        self.assertEqual(form_number({'num_parts': ''}, 'num_parts', 1, int), 1)

    def test_garbage_number_does_not_raise(self):
        self.assertEqual(form_number({'n': 'abc'}, 'n', 7, int), 7)


@unittest.skipUnless(FLASK_AVAILABLE, 'Flask is not installed')
class TestEndpoints(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_health(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'healthy')

    def test_index_renders(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_formats_flag_what_is_measurable(self):
        data = self.client.get('/api/formats').get_json()
        measurable = {f['extension'] for f in data['formats'] if f['measurable']}
        self.assertIn('.step', measurable)
        self.assertNotIn('.prt', measurable)

    def test_analyze_a_real_step_file(self):
        with open(SAMPLE_STEP, 'rb') as handle:
            payload = handle.read()
        response = self.client.post('/api/analyze', data={
            'file': (io.BytesIO(payload), 'sample_bracket.STEP'),
            'process_type': 'cnc_machining',
            'is_symmetric': 'on',
            'num_parts': '',
        }, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body['success'])
        self.assertEqual(body['geometry']['dimensions_mm'], [80.0, 63.0, 25.0])
        self.assertGreaterEqual(body['scores']['dfm_violations'], 1)
        self.assertIn('MEASURED GEOMETRY', body['report'])

    def test_rejects_unknown_extension(self):
        response = self.client.post('/api/analyze', data={
            'file': (io.BytesIO(b'x'), 'notes.txt'),
        }, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)

    def test_missing_file_is_a_400_not_a_crash(self):
        response = self.client.post('/api/analyze', data={},
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)

    def test_download_of_a_missing_report_is_404(self):
        response = self.client.get('/api/download/nope.txt')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
