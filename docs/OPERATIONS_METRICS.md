# Runtime observability

Both maintained adapters provide `GET /metrics` (Prometheus text 0.0.4) and `GET /api/v1/metrics` (JSON schema 1.0). Private-mode reads require the existing bearer, Host and Origin controls; local mode remains loopback-only. Responses are no-store. The example browser gateway denies both telemetry paths by default. A customer must authorize a separate internal collector/network path and verify machine identity, TLS and access/retention controls; these endpoints do not establish that acceptance.

Local synthetic/demo inspection:

```powershell
curl.exe http://127.0.0.1:8000/metrics
curl.exe http://127.0.0.1:8000/api/v1/metrics
```

## What is measured

- Analysis POST responses on exactly `/analyze` and `/api/v1/review`, including authentication/validation/budget errors. Status labels use a fixed allowlist; all other statuses share `other`.
- Response-preparation histograms separately for HTTP200 and non200. HTTP200 does not mean scored, authentic or fully analyzed: it can contain insufficient evidence. Timings begin at adapter dispatch after request headers are parsed, include authorization/body reception/worker wait/serialization, and stop before transmission. They exclude prior gateway/HTTP header waits, network delivery and customer workflows. These are not inference-only timings or an SLA.
- Process uptime, unavailable/out-of-range timing counts and counter saturation.
- Standard-library pre-handler connection-slot rejections, without attributing an unknown route or duration. ASGI/Uvicorn pre-dispatch rejections are **not observed**: JSON reports null and Prometheus omits this counter. Consult Uvicorn and gateway infrastructure telemetry separately.

No document text, decisions, scores, names, IPs, tokens, IDs, model labels, filenames or query strings are retained. The accumulator has fixed route/status/outcome cardinality and fixed histogram buckets; scrapes and unrelated routes do not add samples. Thread-safe snapshots contain no per-request history. Operation counts can still reveal business activity; restrict access and retention.

Counters are process-local and reset on restart; they are not durable audit logs. Each counter is bounded at 2^53-1. Saturation raises `ats_metrics_saturated`; subsequent events for a saturated route are dropped. Floating-point duration sums are approximate. Invalid/missing timings are not recorded as zero. Zero traffic is not proof of availability or healthy analysis.

## Collector interpretation

Monitor `ats_analysis_responses_total` status429 for shared admission pressure, 503 for unavailable work/recovery and 504 for execution deadlines. Auth/validation errors belong to HTTP attempts, not admitted analyses. Separate these from HTTP200 counts; do not label a low aggregate latency dominated by fast denials as good screening latency.

Example latency query, to be evaluated against representative traffic and customer-approved thresholds:

```promql
histogram_quantile(0.95, sum by (le, route) (
  rate(ats_analysis_response_preparation_seconds_bucket{outcome="http_200"}[5m])
))
```

No samples can yield undefined quantiles. Scrape loss, readiness loss, missing-duration/saturation events, sustained 429/503/504 rates and restart loops require their own alerts. Maintain authenticated readiness probes separately; no alert delivery, dashboard or thresholds are installed automatically. A real load plan must also measure memory/CPU/temp use, recovery, gateway rejection, complete-analysis coverage and downstream human-review burden. These metrics do not pass those customer gates.
