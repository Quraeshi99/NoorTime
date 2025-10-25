# project/metrics.py

from prometheus_client import Counter, Histogram

# Define Prometheus metrics

# Cache Metrics
CACHE_HITS = Counter('noortime_cache_hits_total', 'Total cache hits', ['cache_type', 'zone_id', 'year'])
CACHE_MISSES = Counter('noortime_cache_misses_total', 'Total cache misses', ['cache_type', 'zone_id', 'year'])

# API Metrics
API_REQUESTS_TOTAL = Counter('noortime_api_requests_total', 'Total API requests', ['adapter_name', 'endpoint', 'status'])
API_REQUEST_DURATION_SECONDS = Histogram('noortime_api_request_duration_seconds', 'API request duration in seconds', ['adapter_name', 'endpoint'])

# Background Task Metrics
BACKGROUND_TASK_RUNS_TOTAL = Counter('noortime_background_task_runs_total', 'Total background task runs', ['task_name', 'status'])
BACKGROUND_TASK_DURATION_SECONDS = Histogram('noortime_background_task_duration_seconds', 'Background task duration in seconds', ['task_name'])
