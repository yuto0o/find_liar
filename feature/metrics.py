import csv
import logging
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("feature.metrics")


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters = defaultdict(int)
        self._timers = defaultdict(float)

    def inc(self, key: str, n: int = 1):
        with self._lock:
            self._counters[key] += n

    def add(self, key: str, value: int):
        with self._lock:
            self._counters[key] += value

    def record_time(self, key: str, seconds: float):
        with self._lock:
            self._timers[key] += seconds

    def snapshot(self):
        with self._lock:
            return {"counters": dict(self._counters), "timers": dict(self._timers)}

    def persist_snapshot_to_csv(self, csv_path: Optional[str] = None):
        # Append snapshot metrics to a long-form CSV: timestamp,metric,type,value
        csv_path = csv_path or str(
            Path(__file__).resolve().parents[1] / "outputs" / "metrics_timeseries.csv"
        )
        snap = self.snapshot()
        ts = time.time()
        p = Path(csv_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        write_header = not p.exists()
        with p.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["timestamp", "metric", "type", "value"])
            for k, v in snap["counters"].items():
                writer.writerow([ts, k, "counter", v])
            for k, v in snap["timers"].items():
                writer.writerow([ts, k, "timer_seconds_total", f"{v:.6f}"])

    def start_prometheus_exporter(self, port: int = 8000, interval: float = 5.0):
        try:
            from prometheus_client import Gauge, start_http_server
        except Exception:
            logger.warning(
                "prometheus_client not available; prometheus exporter not started"
            )
            return

        # map metric name -> Gauge
        gauges = {}

        def sanitize_name(name: str) -> str:
            return name.replace(".", "_").replace("-", "_")

        def updater():
            start_http_server(port)
            while True:
                snap = self.snapshot()
                for k, v in snap["counters"].items():
                    kn = sanitize_name(k)
                    if kn not in gauges:
                        gauges[kn] = Gauge(kn, f"counter {k}")
                    try:
                        gauges[kn].set(v)
                    except Exception:
                        logger.exception("Failed to set gauge %s", kn)
                for k, v in snap["timers"].items():
                    kn = sanitize_name(k + "_seconds_total")
                    if kn not in gauges:
                        gauges[kn] = Gauge(kn, f"timer {k}")
                    try:
                        gauges[kn].set(v)
                    except Exception:
                        logger.exception("Failed to set gauge %s", kn)
                time.sleep(interval)

        t = threading.Thread(target=updater, daemon=True)
        t.start()

    def report(self) -> str:
        snap = self.snapshot()
        lines = ["=== Metrics ==="]
        for k, v in sorted(snap["counters"].items()):
            lines.append(f"{k}: {v}")
        for k, v in sorted(snap["timers"].items()):
            lines.append(f"{k}_seconds_total: {v:.3f}")
        return "\n".join(lines)


metrics = Metrics()


def log_report():
    logger.info("\n" + metrics.report())
