import subprocess
from ..base import BaseTestCase


class LightstepRunTests(BaseTestCase):
    def test_priority_sampling_from_env(self):
        """
        LIGHTSTEP_METRICS_DISABLE disables runtime metrics
        """
        with self.override_env(dict(LIGHTSTEP_METRICS_DISABLE="True")):
            out = subprocess.check_output(["ls-trace-run", "python", "tests/vendor/lstrace_run_disable_metrics.py"])
            assert out.startswith(b"Test success")
