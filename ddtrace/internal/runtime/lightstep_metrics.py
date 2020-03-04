import logging
import os

from ... import _worker

from .metric_collectors import RuntimeMetricCollector
from .runtime_metrics import RuntimeCollectorsIterable

log = logging.getLogger(__name__)


LS_PROCESS_CPU_TIME_SYS = "process.cpu.system"
LS_PROCESS_CPU_TIME_USER = "process.cpu.user"
LS_PROCESS_MEM_RSS = "process.mem.rss"
LS_SYSTEM_CPU_TIME_SYS = "cpu.system"
LS_SYSTEM_CPU_TIME_USER = "cpu.user"
LS_SYSTEM_CPU_TIME_IDLE = "cpu.idle"
LS_SYSTEM_CPU_TIME_STEAL = "cpu.steal"
LS_SYSTEM_CPU_TIME_NICE = "cpu.nice"
LS_SYSTEM_MEM_AVAIL = "mem.available"
LS_SYSTEM_MEM_USED = "mem.used"
LS_SYSTEM_NET_RECV = "net.recv"
LS_SYSTEM_NET_SENT = "net.sent"

LS_RUNTIME_METRICS = set(
    [
        LS_PROCESS_CPU_TIME_SYS,
        LS_PROCESS_CPU_TIME_USER,
        LS_PROCESS_MEM_RSS,
        LS_SYSTEM_CPU_TIME_SYS,
        LS_SYSTEM_CPU_TIME_USER,
        LS_SYSTEM_CPU_TIME_IDLE,
        LS_SYSTEM_CPU_TIME_STEAL,
        LS_SYSTEM_CPU_TIME_NICE,
        LS_SYSTEM_MEM_AVAIL,
        LS_SYSTEM_MEM_USED,
        LS_SYSTEM_NET_RECV,
        LS_SYSTEM_NET_SENT,
    ]
)


class LightstepPSUtilRuntimeMetricCollector(RuntimeMetricCollector):
    """Collector for psutil metrics.

    Performs batched operations via proc.oneshot() to optimize the calls.
    See https://psutil.readthedocs.io/en/latest/#psutil.Process.oneshot
    for more information.
    """

    required_modules = ["ddtrace.vendor.psutil"]
    stored_value = dict(
        CPU_TIME_SYS_TOTAL=0, CPU_TIME_USER_TOTAL=0, CTX_SWITCH_VOLUNTARY_TOTAL=0, CTX_SWITCH_INVOLUNTARY_TOTAL=0,
    )

    def _on_modules_load(self):
        self.proc = self.modules["ddtrace.vendor.psutil"].Process(os.getpid())
        self.cpu = self.modules["ddtrace.vendor.psutil"].cpu_times
        self.mem = self.modules["ddtrace.vendor.psutil"].virtual_memory
        self.net = self.modules["ddtrace.vendor.psutil"].net_io_counters

    def collect_fn(self, keys):
        with self.proc.oneshot():
            # only return time deltas
            # TODO[tahir]: better abstraction for metrics based on last value
            cpu_time_sys_total = self.proc.cpu_times().system
            cpu_time_user_total = self.proc.cpu_times().user
            cpu_time_sys = cpu_time_sys_total - self.stored_value["CPU_TIME_SYS_TOTAL"]
            cpu_time_user = cpu_time_user_total - self.stored_value["CPU_TIME_USER_TOTAL"]

            system_cpu = self.cpu()
            system_memory = self.mem()
            system_network = self.net()

            self.stored_value = dict(CPU_TIME_SYS_TOTAL=cpu_time_sys_total, CPU_TIME_USER_TOTAL=cpu_time_user_total,)

            metrics = [
                # process metrics
                (LS_PROCESS_CPU_TIME_SYS, cpu_time_sys),
                (LS_PROCESS_CPU_TIME_USER, cpu_time_user),
                (LS_PROCESS_MEM_RSS, self.proc.memory_info().rss),
                # system CPU metrics
                (LS_SYSTEM_CPU_TIME_SYS, system_cpu.system),
                (LS_SYSTEM_CPU_TIME_USER, system_cpu.user),
                (LS_SYSTEM_CPU_TIME_IDLE, system_cpu.idle),
                (LS_SYSTEM_CPU_TIME_NICE, system_cpu.nice),
                # system memory metrics
                (LS_SYSTEM_MEM_AVAIL, system_memory.available),
                (LS_SYSTEM_MEM_USED, system_memory.used),
                # system network metrics
                (LS_SYSTEM_NET_RECV, system_network.bytes_recv),
                (LS_SYSTEM_NET_SENT, system_network.bytes_sent),
            ]

            return metrics


class LightstepRuntimeMetrics(RuntimeCollectorsIterable):
    ENABLED = LS_RUNTIME_METRICS
    COLLECTORS = [
        LightstepPSUtilRuntimeMetricCollector,
    ]


class LightstepMetricsWorker(_worker.PeriodicWorkerThread):
    """ Worker thread to collect and write metrics to a Lightstep endpoint """

    FLUSH_INTERVAL = 30

    def __init__(self, client, flush_interval=FLUSH_INTERVAL):
        super(LightstepMetricsWorker, self).__init__(interval=flush_interval, name=self.__class__.__name__)
        self._client = client
        self._runtime_metrics = LightstepRuntimeMetrics()

    def _to_pb(self):
        for key, value in self._runtime_metrics:
            log.debug("Writing metric %s:%s", key, value)
            # self._statsd_client.gauge(key, value)
        return

    def flush(self):
        self._to_pb()

    run_periodic = flush
    on_shutdown = flush
