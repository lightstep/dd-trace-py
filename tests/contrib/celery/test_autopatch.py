#!/usr/bin/env python
import subprocess
import unittest


class DdtraceRunTest(unittest.TestCase):
    """Test that celery is patched successfully if run with ls-trace-run."""

    def test_autopatch(self):
        out = subprocess.check_output(
            ['ls-trace-run', 'python', 'tests/contrib/celery/autopatch.py']
        )
        assert out.startswith(b'Test success')
