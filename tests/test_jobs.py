"""Tests for the background job runner."""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_dashboard'))

from jobs import JobStore


def wait_for(job, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline and job.status in ('queued', 'running'):
        time.sleep(0.01)
    return job


class TestJobStore(unittest.TestCase):

    def setUp(self):
        self.store = JobStore()

    def test_a_job_runs_and_returns_its_result(self):
        job = wait_for(self.store.submit(lambda job: {'value': 42}))
        self.assertEqual(job.status, 'done')
        self.assertEqual(job.result, {'value': 42})
        self.assertEqual(job.progress, 1.0)

    def test_progress_is_reported_and_clamped(self):
        seen = []

        def work(job):
            job.report(0.5, 'halfway')
            seen.append((job.progress, job.message))
            job.report(5.0, 'over')      # must clamp to 1.0
            seen.append(job.progress)
            job.report(-2.0, 'under')    # must clamp to 0.0
            seen.append(job.progress)
            return None

        wait_for(self.store.submit(work))
        self.assertEqual(seen[0], (0.5, 'halfway'))
        self.assertEqual(seen[1], 1.0)
        self.assertEqual(seen[2], 0.0)

    def test_a_failing_job_records_the_error_rather_than_raising(self):
        def boom(job):
            raise ValueError('bad geometry')

        job = wait_for(self.store.submit(boom))
        self.assertEqual(job.status, 'error')
        self.assertIn('bad geometry', job.error)
        self.assertIsNone(job.result)

    def test_unknown_job_id(self):
        self.assertIsNone(self.store.get('nope'))

    def test_old_jobs_are_pruned(self):
        store = JobStore(max_jobs=3)
        for _ in range(5):
            wait_for(store.submit(lambda job: None))
        self.assertLessEqual(len(store.recent(50)), 3)

    def test_recent_is_newest_first(self):
        first = self.store.submit(lambda job: None, label='first')
        second = self.store.submit(lambda job: None, label='second')
        wait_for(first)
        wait_for(second)
        self.assertEqual(self.store.recent(2)[0].label, 'second')

    def test_result_is_withheld_until_done(self):
        job = wait_for(self.store.submit(lambda job: {'x': 1}))
        self.assertIn('result', job.to_dict())
        self.assertNotIn('result', job.to_dict(include_result=False))


if __name__ == '__main__':
    unittest.main()
