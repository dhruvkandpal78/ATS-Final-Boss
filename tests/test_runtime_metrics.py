import http.client
import json
import threading
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from src.app import asgi, server, metrics as subject
from src.app.security import SecuritySettings


def test_fixed_histograms_separate_success_and_failure_and_ignore_scrapes():
    clock = [10.0]
    metrics = subject.RuntimeMetrics(clock=lambda: clock[0])
    metrics.record("/analyze", "POST", 200, 0.1)
    metrics.record("/analyze", "POST", 429, 0.005)
    metrics.record("/api/v1/review", "POST", 504, 90.1)
    for index in range(1000):
        metrics.record(f"/PRIVATE_NAME_TOKEN_{index}", "POST", 404, 0.1)
        metrics.record(subject.METRICS_JSON_ROUTE, "GET", 200, 0.01)
    clock[0] = 11.5
    snapshot = metrics.snapshot()
    assert snapshot["uptime_seconds"] == 1.5
    route = snapshot["routes"]["/analyze"]
    assert route["responses"] == 2 and route["statuses"]["429"] == 1
    success = route["durations"]["http_200"]
    assert success["count"] == 1 and success["sum_seconds"] == 0.1
    assert [b["count"] for b in success["cumulative_buckets"]][:4] == [0, 0, 1, 1]
    assert "PRIVATE" not in json.dumps(snapshot) + metrics.prometheus()
    assert len(snapshot["routes"]) == 2
    assert 'outcome="http_200",le="+Inf"} 1' in metrics.prometheus()
    snapshot["routes"]["/analyze"]["statuses"]["200"] = 500
    assert metrics.snapshot()["routes"]["/analyze"]["statuses"]["200"] == 1


@pytest.mark.parametrize("duration", [None, True, float("nan"), float("inf"), -1, 3601, 10**1000])
def test_missing_or_invalid_timing_is_not_zero(duration):
    metrics = subject.RuntimeMetrics()
    metrics.record("/analyze", "POST", 599, duration)
    route = metrics.snapshot()["routes"]["/analyze"]
    assert route["statuses"]["other"] == 1 and route["duration_missing"] == 1
    assert route["durations"]["http_non_200"]["count"] == 0


def test_unobserved_connections_are_not_reported_as_zero():
    metrics = subject.RuntimeMetrics()
    assert metrics.snapshot()["connection_rejections"] is None
    assert "ats_connection_rejections_total" not in metrics.prometheus()
    observed = subject.RuntimeMetrics(connection_rejections_observable=True)
    assert observed.snapshot()["connection_rejections"] == 0
    assert "ats_connection_rejections_total 0" in observed.prometheus()


def test_counter_saturation_is_visible_and_bounded(monkeypatch):
    monkeypatch.setattr(subject, "MAX_COUNT", 2)
    metrics = subject.RuntimeMetrics()
    for _ in range(3):
        metrics.record("/analyze", "POST", 503, 1)
        metrics.reject_connection()
    value = metrics.snapshot()
    assert value["counters_saturated"] is True and value["connection_rejections"] == 2
    assert value["routes"]["/analyze"]["responses"] == 2
    assert value["routes"]["/analyze"]["durations"]["http_non_200"]["count"] == 2


def test_concurrent_updates_are_atomic():
    metrics = subject.RuntimeMetrics()
    def update():
        for _ in range(500): metrics.record("/api/v1/review", "POST", 200, 0.05)
    threads = [threading.Thread(target=update) for _ in range(4)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    route = metrics.snapshot()["routes"]["/api/v1/review"]
    assert route["responses"] == route["statuses"]["200"] == 2000
    assert route["durations"]["http_200"]["cumulative_buckets"][-1]["count"] == 2000


@pytest.fixture(params=["asgi", "stdlib"])
def transport(request, monkeypatch):
    settings = SecuritySettings("private", ("testserver", "127.0.0.1"), ("https://hr.example.test",), "test-token", 2)
    def run(payload):
        server.validate_payload(payload)
        return {"synthetic": True}
    if request.param == "asgi":
        # Authorization/dispatch only; production lifespan acceptance is tested separately.
        worker = SimpleNamespace(run=run, close=lambda: None)
        client = TestClient(asgi.create_app(settings=settings, worker=worker))
        def call(method, path, payload=None, authorized=True):
            headers = {"Authorization": "Bearer test-token"} if authorized else {}
            response = client.request(method, path, json=payload, headers=headers)
            return response.status_code, response.text, response.headers
        yield call
        client.close()
    else:
        monkeypatch.setattr(server.WORKER, "run", run)
        instance = server.BoundedHTTPServer(("127.0.0.1", 0), server.Handler, settings)
        thread = threading.Thread(target=instance.serve_forever, daemon=True)
        thread.start()
        def call(method, path, payload=None, authorized=True):
            connection = http.client.HTTPConnection("127.0.0.1", instance.server_port, timeout=3)
            headers = {"Authorization": "Bearer test-token"} if authorized else {}
            body = json.dumps(payload) if payload is not None else None
            if body is not None: headers["Content-Type"] = "application/json"
            connection.request(method, path, body, headers)
            response = connection.getresponse()
            result = response.status, response.read().decode(), dict(response.getheaders())
            connection.close()
            return result
        yield call
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)


def test_both_adapters_require_auth_and_record_denials_validation_and_budget(transport):
    for path in (subject.METRICS_JSON_ROUTE, subject.METRICS_TEXT_ROUTE):
        status, body, headers = transport("GET", path, authorized=False)
        assert status == 401 and "routes" not in body
    assert transport("POST", "/analyze", {"text": "PRIVATE_CANARY"}, authorized=False)[0] == 401
    assert transport("POST", "/analyze", {})[0] == 422
    assert transport("POST", "/analyze", {"text": "PRIVATE_CANARY"})[0] == 200
    assert transport("POST", "/analyze", {"text": "PRIVATE_CANARY"})[0] == 429
    status, body, headers = transport("GET", subject.METRICS_JSON_ROUTE)
    value = json.loads(body)
    route = value["routes"]["/analyze"]
    assert status == 200 and route["responses"] == 4
    assert {s: route["statuses"][s] for s in ("200", "401", "422", "429")} == {"200": 1, "401": 1, "422": 1, "429": 1}
    assert "PRIVATE_CANARY" not in body
    status, text, headers = transport("GET", subject.METRICS_TEXT_ROUTE)
    assert status == 200 and 'status="429"} 1' in text and "PRIVATE_CANARY" not in text
    assert next(v for k, v in headers.items() if k.lower() == "cache-control") == "no-store"
    after = json.loads(transport("GET", subject.METRICS_JSON_ROUTE)[1])
    assert after["routes"] == value["routes"]
