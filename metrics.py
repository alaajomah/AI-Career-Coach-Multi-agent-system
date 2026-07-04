from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "career_requests_total",
    "Total requests"
)

ERROR_COUNT = Counter(
    "career_errors_total",
    "Total errors"
)

LATENCY = Histogram(
    "career_request_latency_seconds",
    "Request latency"
)