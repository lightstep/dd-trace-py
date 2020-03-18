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
from ddtrace.vendor.lightstep.constants import COMPONENT_NAME, SERVICE_VERSION
from ddtrace.vendor.lightstep.metrics_pb2 import IngestRequest, MetricKind

_log = logging.getLogger(__name__)


LS_PROCESS_CPU_TIME_SYS = "runtime.python.cpu.sys"
LS_PROCESS_CPU_TIME_USER = "runtime.python.cpu.user"
LS_PROCESS_MEM_RSS = "runtime.python.mem.rss"
LS_SYSTEM_CPU_TIME_SYS = "cpu.sys"
LS_SYSTEM_CPU_TIME_USER = "cpu.user"
LS_SYSTEM_CPU_TIME_TOTAL = "cpu.total"
LS_SYSTEM_CPU_TIME_USAGE = "cpu.usage"
LS_SYSTEM_MEM_AVAIL = "mem.available"
LS_SYSTEM_MEM_USED = "mem.total"
LS_SYSTEM_NET_RECV = "net.bytes_recv"
LS_SYSTEM_NET_SENT = "net.bytes_sent"

LS_RUNTIME_METRICS = set(
    [
        LS_PROCESS_CPU_TIME_SYS,
        LS_PROCESS_CPU_TIME_USER,
        LS_PROCESS_MEM_RSS,
        LS_SYSTEM_CPU_TIME_SYS,
        LS_SYSTEM_CPU_TIME_USER,
        LS_SYSTEM_CPU_TIME_TOTAL,
        LS_SYSTEM_CPU_TIME_USAGE,
        LS_SYSTEM_MEM_AVAIL,
        LS_SYSTEM_MEM_USED,
        LS_SYSTEM_NET_RECV,
        LS_SYSTEM_NET_SENT,
    ]
)

_HOSTNAME_KEY = "lightstep.hostname"
_REPORTER_PLATFORM_KEY = "lightstep.reporter_platform"
_REPORTER_PLATFORM_VERSION_KEY = "lightstep.reporter_platform_version"
_REPORTER_VERSION_KEY = "lightstep.reporter_version"


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
        SYSTEM_CPU_SYS_TOTAL=0,
        SYSTEM_CPU_USER_TOTAL=0,
        SYSTEM_CPU_TOTAL=0,
        SYSTEM_CPU_USAGE_TOTAL=0,
        NET_RECV_TOTAL=0,
        NET_SENT_TOTAL=0,
    )
    previous_value = dict()
    _skipped_first = False

    def _on_modules_load(self):
        self.proc = self.modules["ddtrace.vendor.psutil"].Process(os.getpid())
        self.cpu = self.modules["ddtrace.vendor.psutil"].cpu_times
        self.mem = self.modules["ddtrace.vendor.psutil"].virtual_memory
        self.net = self.modules["ddtrace.vendor.psutil"].net_io_counters

    def _usage(self):
        cpu_times = self.cpu()
        usage = cpu_times.user + cpu_times.system
        metrics = [
            "nice",
            "iowait",
            "irq",
            "softirq",
            "steal",
        ]
        for m in metrics:
            if hasattr(cpu_times, m):
                usage += getattr(cpu_times, m)

        return usage

    def _measure(self):
        cpu_time_sys_total = self.proc.cpu_times().system
        cpu_time_user_total = self.proc.cpu_times().user
        cpu_time_sys = cpu_time_sys_total - self.stored_value["CPU_TIME_SYS_TOTAL"]
        cpu_time_user = cpu_time_user_total - self.stored_value["CPU_TIME_USER_TOTAL"]

        system_cpu_sys_total = self.cpu().system
        system_cpu_user_total = self.cpu().user
        system_cpu_usage_total = self._usage()
        system_cpu_total_total = self.cpu().idle + system_cpu_usage_total

        system_cpu_sys = system_cpu_sys_total - self.stored_value["SYSTEM_CPU_SYS_TOTAL"]
        system_cpu_user = system_cpu_user_total - self.stored_value["SYSTEM_CPU_USER_TOTAL"]
        system_cpu_usage = system_cpu_usage_total - self.stored_value["SYSTEM_CPU_USAGE_TOTAL"]
        system_cpu_total = system_cpu_total_total - self.stored_value["SYSTEM_CPU_TOTAL"]

        net_recv_total = self.net().bytes_recv
        net_sent_total = self.net().bytes_sent
        net_recv = net_recv_total - self.stored_value["NET_RECV_TOTAL"]
        net_sent = net_sent_total - self.stored_value["NET_SENT_TOTAL"]

        system_memory = self.mem()

        self.previous_value = self.stored_value

        self.stored_value = dict(
            CPU_TIME_SYS_TOTAL=cpu_time_sys_total,
            CPU_TIME_USER_TOTAL=cpu_time_user_total,
            SYSTEM_CPU_SYS_TOTAL=system_cpu_sys_total,
            SYSTEM_CPU_USER_TOTAL=system_cpu_user_total,
            SYSTEM_CPU_TOTAL=system_cpu_total_total,
            SYSTEM_CPU_USAGE_TOTAL=system_cpu_usage_total,
            NET_RECV_TOTAL=net_recv_total,
            NET_SENT_TOTAL=net_sent_total,
        )

        return [
            # process metrics
            (LS_PROCESS_CPU_TIME_SYS, cpu_time_sys, MetricKind.COUNTER),
            (LS_PROCESS_CPU_TIME_USER, cpu_time_user, MetricKind.COUNTER),
            (LS_PROCESS_MEM_RSS, self.proc.memory_info().rss, MetricKind.GAUGE),
            # system CPU metrics
            (LS_SYSTEM_CPU_TIME_SYS, system_cpu_sys, MetricKind.COUNTER),
            (LS_SYSTEM_CPU_TIME_USER, system_cpu_user, MetricKind.COUNTER),
            (LS_SYSTEM_CPU_TIME_TOTAL, system_cpu_total, MetricKind.COUNTER),
            (LS_SYSTEM_CPU_TIME_USAGE, system_cpu_usage, MetricKind.COUNTER),
            # system memory metrics
            (LS_SYSTEM_MEM_AVAIL, system_memory.available, MetricKind.GAUGE),
            (LS_SYSTEM_MEM_USED, system_memory.used, MetricKind.GAUGE),
            # system network metrics
            (LS_SYSTEM_NET_RECV, net_recv, MetricKind.COUNTER),
            (LS_SYSTEM_NET_SENT, net_sent, MetricKind.COUNTER),
        ]

    def collect_fn(self, keys):
        with self.proc.oneshot():
            metrics = self._measure()
            if not self._skipped_first:
                # intentionally skip the initial set of metrics
                self._skipped_first = True
                metrics = self._measure()
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

    _flush_interval = 30
    _key_length = 30

    def __init__(self, client, flush_interval=_flush_interval, tracer_tags={}):
        super(LightstepMetricsWorker, self).__init__(interval=flush_interval, name=self.__class__.__name__)
        self._component_name = tracer_tags.get(COMPONENT_NAME)
        self._service_version = tracer_tags.get(SERVICE_VERSION)

        self._client = client
        self._runtime_metrics = LightstepRuntimeMetrics()
        self._reporter = Reporter(
            tags=[
                KeyValue(key=COMPONENT_NAME, string_value=self._component_name),
                KeyValue(key=SERVICE_VERSION, string_value=self._service_version),
                KeyValue(key=_HOSTNAME_KEY, string_value=os.uname()[1]),
                KeyValue(key=_REPORTER_PLATFORM_KEY, string_value="python"),
                KeyValue(key=_REPORTER_PLATFORM_VERSION_KEY, string_value=platform.python_version()),
            ]
        )
        self._intervals = 1
        self._labels = [
            KeyValue(key=COMPONENT_NAME, string_value=self._component_name),
            KeyValue(key=SERVICE_VERSION, string_value=self._service_version),
            KeyValue(key=_HOSTNAME_KEY, string_value=os.uname()[1]),
        ]

    def _ingest_request(self):
        """ Interate through the metrics and create an IngestRequest
        """
        request = IngestRequest(reporter=self._reporter)
        request.idempotency_key = self._generate_idempotency_key()
        start_time = Timestamp()
        start_time.GetCurrentTime()
        duration = Duration()
        duration.FromSeconds(self._intervals * self._flush_interval)
        for metric in self._runtime_metrics:
            metric_type = MetricKind.GAUGE
            if len(metric) == 3:
                key, value, metric_type = metric
            else:
                key, value = metric
            request.points.add(
                duration=duration,
                start=start_time,
                labels=self._labels,
                metric_name=key,
                double_value=value,
                kind=metric_type,
            )
        _log.debug("Metrics collected: %s", request)
        return request

    def _generate_idempotency_key(self):
        return "".join(random.choice(string.ascii_lowercase) for i in range(self._key_length))

    def flush(self):
        ingest_request = self._ingest_request()
        try:
            self._client.send(ingest_request.SerializeToString())
            self._intervals = 1
        except Exception:
            _log.debug("failed request: %s", ingest_request.idempotency_key)
            self._runtime_metrics.rollback()
            self._intervals += 1

    run_periodic = flush
    on_shutdown = flush
