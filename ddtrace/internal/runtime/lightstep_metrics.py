import logging
import os
import platform
import random
import string

from ... import _worker

from .constants import GC_RUNTIME_METRICS
from .metric_collectors import GCRuntimeMetricCollector, RuntimeMetricCollector
from .runtime_metrics import RuntimeCollectorsIterable
from google.protobuf.duration_pb2 import Duration
from google.protobuf.timestamp_pb2 import Timestamp
from ddtrace.vendor.lightstep.collector_pb2 import KeyValue, Reporter
from ddtrace.vendor.lightstep.metrics_pb2 import IngestRequest, MetricKind

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
        CPU_TIME_SYS_TOTAL=0,
        CPU_TIME_USER_TOTAL=0,
        SYSTEM_CPU_TOTAL=0,
        SYSTEM_CPU_USER_TOTAL=0,
        SYSTEM_CPU_IDLE_TOTAL=0,
        SYSTEM_CPU_NICE_TOTAL=0,
        NET_RECV_TOTAL=0,
        NET_SENT_TOTAL=0,
    )
    previous_value = dict()

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

            system_cpu_total = self.cpu().system
            system_cpu_user_total = self.cpu().user
            system_cpu_idle_total = self.cpu().idle
            system_cpu_nice_total = self.cpu().nice
            system_cpu = system_cpu_total - self.stored_value["SYSTEM_CPU_TOTAL"]
            system_cpu_user = system_cpu_user_total - self.stored_value["SYSTEM_CPU_USER_TOTAL"]
            system_cpu_idle = system_cpu_idle_total - self.stored_value["SYSTEM_CPU_IDLE_TOTAL"]
            system_cpu_nice = system_cpu_nice_total - self.stored_value["SYSTEM_CPU_NICE_TOTAL"]

            net_recv_total = self.net().bytes_recv
            net_sent_total = self.net().bytes_sent
            net_recv = net_recv_total - self.stored_value["NET_RECV_TOTAL"]
            net_sent = net_sent_total - self.stored_value["NET_SENT_TOTAL"]

            system_memory = self.mem()

            self.previous_value = self.stored_value

            self.stored_value = dict(
                CPU_TIME_SYS_TOTAL=cpu_time_sys_total,
                CPU_TIME_USER_TOTAL=cpu_time_user_total,
                SYSTEM_CPU_TOTAL=system_cpu_total,
                SYSTEM_CPU_USER_TOTAL=system_cpu_user_total,
                SYSTEM_CPU_IDLE_TOTAL=system_cpu_idle_total,
                SYSTEM_CPU_NICE_TOTAL=system_cpu_nice_total,
                NET_RECV_TOTAL=net_recv_total,
                NET_SENT_TOTAL=net_sent_total,
            )

            metrics = [
                # process metrics
                (LS_PROCESS_CPU_TIME_SYS, cpu_time_sys, MetricKind.COUNTER),
                (LS_PROCESS_CPU_TIME_USER, cpu_time_user, MetricKind.COUNTER),
                (LS_PROCESS_MEM_RSS, self.proc.memory_info().rss, MetricKind.GAUGE),
                # system CPU metrics
                (LS_SYSTEM_CPU_TIME_SYS, system_cpu, MetricKind.COUNTER),
                (LS_SYSTEM_CPU_TIME_USER, system_cpu_user, MetricKind.COUNTER),
                (LS_SYSTEM_CPU_TIME_IDLE, system_cpu_idle, MetricKind.COUNTER),
                (LS_SYSTEM_CPU_TIME_NICE, system_cpu_nice, MetricKind.COUNTER),
                # system memory metrics
                (LS_SYSTEM_MEM_AVAIL, system_memory.available, MetricKind.GAUGE),
                (LS_SYSTEM_MEM_USED, system_memory.used, MetricKind.GAUGE),
                # system network metrics
                (LS_SYSTEM_NET_RECV, net_recv, MetricKind.COUNTER),
                (LS_SYSTEM_NET_SENT, net_sent, MetricKind.COUNTER),
            ]

            return metrics

    def rollback(self):
        self.stored_value = self.previous_value


class LightstepRuntimeMetrics(RuntimeCollectorsIterable):
    ENABLED = GC_RUNTIME_METRICS | LS_RUNTIME_METRICS
    COLLECTORS = [
        GCRuntimeMetricCollector,
        LightstepPSUtilRuntimeMetricCollector,
    ]

    def rollback(self):
        for c in self._collectors:
            if hasattr(c, "rollback"):
                c.rollback()


class LightstepMetricsWorker(_worker.PeriodicWorkerThread):
    """ Worker thread to collect and write metrics to a Lightstep endpoint """

    FLUSH_INTERVAL = 5
    KEY_LENGTH = 30

    def __init__(self, client, flush_interval=FLUSH_INTERVAL):
        super(LightstepMetricsWorker, self).__init__(interval=flush_interval, name=self.__class__.__name__)
        self._client = client
        self._runtime_metrics = LightstepRuntimeMetrics()
        self._reporter = Reporter(tags=[
            # TODO: pull the component name from the global tags if possible
            KeyValue(key="lightstep.component_name", string_value=os.getenv("LIGHTSTEP_COMPONENT_NAME")),
            KeyValue(key="lightstep.hostname", string_value=os.uname()[1]),
            KeyValue(key="lightstep.reporter_platform", string_value="ls-trace-py"),
            KeyValue(key="lightstep.reporter_platform_version", string_value=platform.python_version())
        ])
        self._retries = 1
    
    def _ingest_request(self):
        """ Interate through the metrics and create an IngestRequest
        """
        request = IngestRequest(reporter=self._reporter)
        request.idempotency_key = self._generate_idempotency_key()
        start_time = Timestamp()
        start_time.GetCurrentTime()
        labels = [
            KeyValue(key="lightstep.component_name", string_value=os.getenv("LIGHTSTEP_COMPONENT_NAME")),
        ]
        duration = Duration()
        duration.FromSeconds(self._retries * self.FLUSH_INTERVAL)
        for metric in self._runtime_metrics:
            metric_type = MetricKind.GAUGE
            if len(metric) == 3:
                key, value, metric_type = metric
            else:
                key, value = metric
            point = request.points.add(
                duration=duration,
                start=start_time,
                labels=labels,
                metric_name=key,
                double_value=value,
                kind=metric_type,
            )
        log.debug("Metrics collected: {}".format(request))
        return request

    def _generate_idempotency_key(self):
        return "".join(random.choice(string.ascii_lowercase) for i in range(self.KEY_LENGTH))

    def flush(self):
        ingest_request = self._ingest_request()
        try:
            self._client.send(ingest_request.SerializeToString())
            self._retries = 1
        except Exception:
            log.debug("failed request: {}".format(ingest_request.idempotency_key))
            self._runtime_metrics.rollback()
            self._retries += 1

    run_periodic = flush
    on_shutdown = flush
