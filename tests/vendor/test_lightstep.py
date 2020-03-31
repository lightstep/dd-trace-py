import subprocess
from ..base import BaseTestCase


class LightstepRunTests(BaseTestCase):
    def test_priority_sampling_from_env(self):
        """
        LS_METRICS_ENABLED disables runtime metrics
        """
        with self.override_env(dict(LS_METRICS_ENABLED="False")):
            out = subprocess.check_output(["ls-trace-run", "python", "tests/vendor/lstrace_run_disable_metrics.py"])
            assert out.startswith(b"Test success")
