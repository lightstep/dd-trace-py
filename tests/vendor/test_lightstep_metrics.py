from mock import Mock, patch

from ..base import BaseTestCase
from ddtrace import tracer
from ddtrace.internal.runtime.constants import GC_RUNTIME_METRICS
from ddtrace.internal.runtime.lightstep_metrics import (
    LightstepMetricsWorker,
    LightstepPSUtilRuntimeMetricCollector,
    LightstepRuntimeMetrics,
    LS_RUNTIME_METRICS,
    LS_PROCESS_CPU_TIME_SYS,
    LS_PROCESS_CPU_TIME_USER,
    LS_PROCESS_MEM_RSS,
    LS_SYSTEM_CPU_TIME_SYS,
    LS_SYSTEM_CPU_TIME_USER,
    LS_SYSTEM_CPU_TIME_TOTAL,
    LS_SYSTEM_CPU_TIME_USAGE,
    LS_SYSTEM_MEM_AVAIL,
    LS_SYSTEM_MEM_TOTAL,
    LS_SYSTEM_NET_RECV,
    LS_SYSTEM_NET_SENT,
)
from ddtrace.vendor.lightstep.constants import COMPONENT_NAME, SERVICE_NAME, SERVICE_VERSION
from ddtrace.vendor.lightstep.metrics_pb2 import MetricKind


# TODO:
# - test total > usage
# - if a client fails to send, duration for the following
#   request shows 2x intervals


class TestLightstepPSUtilRuntimeMetricCollector(BaseTestCase):
    def test_skipped_first(self):
        collector = LightstepPSUtilRuntimeMetricCollector()
        self.assertFalse(collector._skipped_first)
        collector.collect_fn({})
        self.assertTrue(collector._skipped_first)

    def test_usage(self):
        collector = LightstepPSUtilRuntimeMetricCollector()
        values = {
            "nice": 10,
            "steal": 11,
            "user": 12,
            "system": 13,
            "softirq": 14,
            "irq": 15,
            "iowait": 16,
        }
        mock_cpu_times = Mock(**values)
        expected = 0
        for _, v in values.items():
            expected += v

        collector.cpu
        with patch.object(collector, "cpu") as mock_cpu:
            mock_cpu.return_value = mock_cpu_times
            self.assertEqual(collector._usage(), expected)

    def test_measure(self):
        self.maxDiff = None
        mock_cpu_times = Mock()
        mock_cpu_times.nice = 10
        mock_cpu_times.steal = 11
        mock_cpu_times.user = 12
        mock_cpu_times.system = 13
        mock_cpu_times.softirq = 14
        mock_cpu_times.irq = 15
        mock_cpu_times.iowait = 16
        mock_cpu_times.idle = 17

        attrs = {"cpu_times.return_value": mock_cpu_times, "memory_info.return_value": Mock(rss=10000)}
        mock_proc = Mock(**attrs)

        attrs = {"available": 100, "total": 200}
        mock_mem = Mock(**attrs)

        attrs = {"bytes_recv": 1000, "bytes_sent": 1000}
        mock_net = Mock(**attrs)

        expected = [
            (LS_PROCESS_CPU_TIME_SYS, mock_cpu_times.system, MetricKind.COUNTER),
            (LS_PROCESS_CPU_TIME_USER, mock_cpu_times.user, MetricKind.COUNTER),
            (LS_PROCESS_MEM_RSS, mock_proc.memory_info().rss, MetricKind.GAUGE),
            (LS_SYSTEM_CPU_TIME_SYS, mock_cpu_times.system, MetricKind.COUNTER),
            (LS_SYSTEM_CPU_TIME_USER, mock_cpu_times.user, MetricKind.COUNTER),
            (LS_SYSTEM_CPU_TIME_TOTAL, 108, MetricKind.COUNTER),
            (LS_SYSTEM_CPU_TIME_USAGE, 91, MetricKind.COUNTER),
            (LS_SYSTEM_MEM_AVAIL, mock_mem.available, MetricKind.GAUGE),
            (LS_SYSTEM_MEM_TOTAL, mock_mem.total, MetricKind.GAUGE),
            (LS_SYSTEM_NET_RECV, mock_net.bytes_recv, MetricKind.COUNTER),
            (LS_SYSTEM_NET_SENT, mock_net.bytes_sent, MetricKind.COUNTER),
        ]
        collector = LightstepPSUtilRuntimeMetricCollector()
        with patch.object(collector, "cpu") as mock_cpu_call:
            mock_cpu_call.return_value = mock_cpu_times
            collector.proc = mock_proc
            with patch.object(collector, "net") as mock_net_call:
                mock_net_call.return_value = mock_net
                with patch.object(collector, "mem") as mock_mem_call:
                    mock_mem_call.return_value = mock_mem
                    self.assertEqual(collector._measure(), expected)


class TestLightstepRuntimeMetrics(BaseTestCase):
    def test_all_metrics(self):
        metrics = set()
        for k in LightstepRuntimeMetrics():
            metrics.add(k[0])
        self.assertSetEqual(metrics, GC_RUNTIME_METRICS | LS_RUNTIME_METRICS)


class TestLightstepMetricsWorker(BaseTestCase):
    def test_idempotency_key(self):
        worker = LightstepMetricsWorker(Mock())
        self.assertNotEqual(
            worker._generate_idempotency_key(), worker._generate_idempotency_key(),
        )

    def test_ingest_request(self):
        # test that ingest request is created successfully
        worker = LightstepMetricsWorker(Mock())
        req = worker._ingest_request()
        self.assertEqual(len(req.reporter.tags), 5)
        self.assertEqual(len(worker._labels), 3)

        # update tags
        tracer.set_tags({
            SERVICE_NAME: "test-component",
            SERVICE_VERSION: "vTest"
        })

        req = worker._ingest_request()
        self.assertEqual(len(req.reporter.tags), 5)
        self.assertEqual(len(worker._labels), 3)
        for tag in req.reporter.tags:
            if tag.key == COMPONENT_NAME:
                self.assertEqual(tag.string_value, "test-component")
            if tag.key == SERVICE_VERSION:
                self.assertEqual(tag.string_value, "vTest")

        for label in worker._labels:
            if label.key == COMPONENT_NAME:
                self.assertEqual(label.string_value, "test-component")
            if label.key == SERVICE_VERSION:
                self.assertEqual(label.string_value, "vTest")

        req = worker._ingest_request()
        self.assertEqual(len(req.reporter.tags), 5)
        self.assertEqual(len(worker._labels), 3)
