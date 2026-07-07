# src/services/metrics_service.py - NEW

import time
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram, generate_latest


class MetricsService:
    """Service for collecting platform metrics"""

    # Counters
    dashboard_requests = Counter(
        "dashboard_requests_total", "Total dashboard requests", ["tenant_id", "source"]
    )
    cache_hits = Counter("cache_hits_total", "Cache hits", ["tenant_id", "cache_type"])
    cache_misses = Counter(
        "cache_misses_total", "Cache misses", ["tenant_id", "cache_type"]
    )
    uploads_total = Counter("uploads_total", "Total uploads", ["tenant_id", "status"])

    # Histograms
    dashboard_duration = Histogram(
        "dashboard_duration_seconds", "Dashboard request duration", ["source"]
    )
    upload_duration = Histogram(
        "upload_duration_seconds", "Upload processing duration", ["tenant_id"]
    )
    worker_duration = Histogram(
        "worker_duration_seconds", "Worker processing duration", ["worker_type"]
    )

    # Gauges
    active_workers = Gauge("active_workers", "Number of active workers")
    pending_uploads = Gauge(
        "pending_uploads", "Number of pending uploads", ["tenant_id"]
    )
    snapshot_age = Gauge(
        "snapshot_age_seconds", "Age of analytics snapshot", ["tenant_id"]
    )
    health_score = Gauge("health_score_value", "Health score value", ["tenant_id"])

    @classmethod
    @contextmanager
    def measure_duration(cls, metric):
        """Context manager for measuring duration"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            if isinstance(metric, Histogram):
                metric.observe(duration)

    @classmethod
    def track_dashboard_request(cls, tenant_id: str, source: str):
        cls.dashboard_requests.labels(tenant_id=tenant_id, source=source).inc()

    @classmethod
    def track_cache_hit(cls, tenant_id: str, cache_type: str):
        cls.cache_hits.labels(tenant_id=tenant_id, cache_type=cache_type).inc()

    @classmethod
    def track_cache_miss(cls, tenant_id: str, cache_type: str):
        cls.cache_misses.labels(tenant_id=tenant_id, cache_type=cache_type).inc()

    @classmethod
    def track_upload(cls, tenant_id: str, status: str):
        cls.uploads_total.labels(tenant_id=tenant_id, status=status).inc()

    @classmethod
    def set_health_score(cls, tenant_id: str, score: int):
        cls.health_score.labels(tenant_id=tenant_id).set(score)

    @classmethod
    def get_metrics(cls):
        """Get all metrics as string (for /metrics endpoint)"""
        return generate_latest()
