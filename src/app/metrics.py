"""Fixed-cardinality, process-local HTTP metrics; no candidate/request labels."""
import math
import threading
from time import monotonic

METRICS_JSON_ROUTE = "/api/v1/metrics"
METRICS_TEXT_ROUTE = "/metrics"
ANALYSIS_ROUTES = ("/analyze", "/api/v1/review")
STATUSES = (200, 400, 401, 403, 408, 413, 415, 422, 429, 503, 504)
BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 90, 120)
MAX_COUNT = 2**53 - 1


class RuntimeMetrics:
    def __init__(self, clock=monotonic, *, connection_rejections_observable=False):
        self._clock, self._started = clock, clock()
        self._lock = threading.Lock()
        self._saturated = False
        self._connection_rejections = 0
        self._connection_rejections_observable = connection_rejections_observable
        self._routes = {route: {
            "responses": 0, "statuses": {str(status): 0 for status in (*STATUSES, "other")},
            "duration_missing": 0,
            "durations": {kind: {"count": 0, "sum_seconds": 0.0, "buckets": [0] * len(BUCKETS)}
                          for kind in ("http_200", "http_non_200")}}
                        for route in ANALYSIS_ROUTES}

    def reject_connection(self):
        """Pre-handler stdlib slot rejection; route/status timing is unknown."""
        with self._lock:
            self._connection_rejections_observable = True
            if self._connection_rejections < MAX_COUNT:
                self._connection_rejections += 1
            else:
                self._saturated = True

    def record(self, path, method, status, seconds):
        if method != "POST" or path not in ANALYSIS_ROUTES:
            return
        key = str(status) if type(status) is int and status in STATUSES else "other"
        valid_duration = type(seconds) in (int, float) and 0 <= seconds <= 3600 and math.isfinite(seconds)
        with self._lock:
            route = self._routes[path]
            if route["responses"] == MAX_COUNT:
                self._saturated = True
                return
            route["responses"] += 1
            route["statuses"][key] += 1
            if not valid_duration:
                route["duration_missing"] += 1
                return
            sample = route["durations"]["http_200" if status == 200 else "http_non_200"]
            sample["count"] += 1
            sample["sum_seconds"] += seconds
            for index, bound in enumerate(BUCKETS):
                sample["buckets"][index] += int(seconds <= bound)

    def snapshot(self):
        with self._lock:
            routes = {path: {
                "responses": route["responses"], "statuses": dict(route["statuses"]),
                "duration_missing": route["duration_missing"],
                "durations": {kind: {"count": sample["count"], "sum_seconds": sample["sum_seconds"],
                    "cumulative_buckets": [{"le_seconds": bound, "count": count}
                                           for bound, count in zip(BUCKETS, sample["buckets"]) ]}
                              for kind, sample in route["durations"].items()}}
                      for path, route in self._routes.items()}
            return {"schema_version": "1.0", "scope": "process_local_analysis_http",
                    "timing_scope": "dispatch_to_response_prepared",
                    "uptime_seconds": max(0, self._clock() - self._started),
                    "counters_saturated": self._saturated,
                    "connection_rejections": self._connection_rejections if self._connection_rejections_observable else None,
                    "routes": routes}

    def prometheus(self):
        value = self.snapshot()
        lines = ["# HELP ats_analysis_responses_total Prepared analysis HTTP responses by fixed route/status.",
                 "# TYPE ats_analysis_responses_total counter"]
        for route, stats in value["routes"].items():
            for status, count in stats["statuses"].items():
                lines.append(f'ats_analysis_responses_total{{route="{route}",status="{status}"}} {count}')
        lines.extend(["# HELP ats_analysis_response_preparation_seconds Time to prepare an analysis response, excluding transmission.",
                      "# TYPE ats_analysis_response_preparation_seconds histogram"])
        for route, stats in value["routes"].items():
            for outcome, sample in stats["durations"].items():
                labels = f'route="{route}",outcome="{outcome}"'
                for bucket in sample["cumulative_buckets"]:
                    lines.append(f'ats_analysis_response_preparation_seconds_bucket{{{labels},le="{bucket["le_seconds"]}"}} {bucket["count"]}')
                lines.append(f'ats_analysis_response_preparation_seconds_bucket{{{labels},le="+Inf"}} {sample["count"]}')
                lines.append(f'ats_analysis_response_preparation_seconds_count{{{labels}}} {sample["count"]}')
                lines.append(f'ats_analysis_response_preparation_seconds_sum{{{labels}}} {sample["sum_seconds"]}')
        for name, kind, number in (
            ("ats_analysis_duration_missing_total", "counter", sum(r["duration_missing"] for r in value["routes"].values())),
            ("ats_process_uptime_seconds", "gauge", value["uptime_seconds"]),
            ("ats_metrics_saturated", "gauge", int(value["counters_saturated"]))):
            lines.extend([f"# TYPE {name} {kind}", f"{name} {number}"])
        if value["connection_rejections"] is not None:
            lines.extend(["# TYPE ats_connection_rejections_total counter",
                          f'ats_connection_rejections_total {value["connection_rejections"]}'])
        return "\n".join(lines) + "\n"
