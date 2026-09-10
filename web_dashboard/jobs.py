"""A small in-process background job runner for the dashboard.

Analysis can take a while - ray casting wall thickness over a dense mesh is
the slow part - so uploads are queued and run on a worker thread while the
browser polls for progress.

Standard library only. Jobs live in memory: they are lost when the server
restarts, which is the right trade for a local engineering tool.
"""

import threading
import traceback
import uuid
from collections import OrderedDict
from datetime import datetime

# How many finished jobs to keep before the oldest are dropped.
MAX_JOBS = 50


class Job:
    """One unit of background work and everything the UI needs to show it."""

    def __init__(self, job_id, label):
        self.id = job_id
        self.label = label
        self.status = 'queued'          # queued | running | done | error
        self.progress = 0.0             # 0.0 to 1.0
        self.message = 'Queued'
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.finished_at = None

    def report(self, fraction, message):
        """Progress callback handed to the worker function."""
        self.progress = max(0.0, min(1.0, float(fraction)))
        self.message = message

    def to_dict(self, include_result=True):
        payload = {
            'job_id': self.id,
            'label': self.label,
            'status': self.status,
            'progress': round(self.progress, 3),
            'message': self.message,
            'created_at': self.created_at.isoformat(timespec='seconds'),
            'finished_at': (self.finished_at.isoformat(timespec='seconds')
                            if self.finished_at else None),
            'error': self.error,
        }
        if include_result and self.status == 'done':
            payload['result'] = self.result
        return payload


class JobStore:
    """Thread-safe registry of jobs, newest last."""

    def __init__(self, max_jobs=MAX_JOBS):
        self._jobs = OrderedDict()
        self._lock = threading.Lock()
        self._max_jobs = max_jobs

    def submit(self, function, label='Analysis'):
        """Run ``function(job)`` on a worker thread and return the Job."""
        job = Job(uuid.uuid4().hex[:12], label)
        with self._lock:
            self._jobs[job.id] = job
            self._prune()

        thread = threading.Thread(target=self._run, args=(job, function),
                                  daemon=True)
        thread.start()
        return job

    def _run(self, job, function):
        job.status = 'running'
        job.message = 'Starting'
        try:
            job.result = function(job)
            job.progress = 1.0
            job.status = 'done'
            job.message = 'Complete'
        except Exception as error:  # noqa: BLE001 - reported to the browser
            # Log first: a caller watching for 'error' would otherwise race
            # the traceback being written.
            traceback.print_exc()
            job.error = '%s: %s' % (type(error).__name__, error)
            job.message = 'Failed'
            job.status = 'error'
        finally:
            job.finished_at = datetime.now()

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def recent(self, limit=10):
        with self._lock:
            jobs = list(self._jobs.values())
        return list(reversed(jobs))[:limit]

    def _prune(self):
        while len(self._jobs) > self._max_jobs:
            self._jobs.popitem(last=False)
