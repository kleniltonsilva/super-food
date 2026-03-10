# backend/app/metrics.py

"""
Metricas de Performance - Super Food API
Contadores in-memory para monitoramento basico
"""

import time
import threading
from collections import defaultdict
from typing import Dict, Any


class MetricsCollector:
    """Coleta metricas de performance in-memory"""

    def __init__(self):
        self._lock = threading.Lock()
        self._request_count = 0
        self._error_count = 0
        self._status_counts: Dict[int, int] = defaultdict(int)
        self._latencies: list = []
        self._max_latencies = 10000  # Mantém últimas 10k medições
        self._start_time = time.time()

    def record_request(self, status_code: int, duration_ms: float):
        """Registra uma requisicao processada"""
        with self._lock:
            self._request_count += 1
            self._status_counts[status_code] += 1
            if status_code >= 400:
                self._error_count += 1
            self._latencies.append(duration_ms)
            if len(self._latencies) > self._max_latencies:
                self._latencies = self._latencies[-self._max_latencies:]

    def get_percentile(self, p: float) -> float:
        """Calcula percentil das latencias"""
        if not self._latencies:
            return 0.0
        sorted_lat = sorted(self._latencies)
        idx = int(len(sorted_lat) * p / 100)
        idx = min(idx, len(sorted_lat) - 1)
        return round(sorted_lat[idx], 2)

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna snapshot das metricas"""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                "uptime_seconds": round(uptime, 0),
                "total_requests": self._request_count,
                "total_errors": self._error_count,
                "error_rate": round(self._error_count / max(self._request_count, 1) * 100, 2),
                "requests_per_second": round(self._request_count / max(uptime, 1), 2),
                "status_codes": dict(self._status_counts),
                "latency": {
                    "p50_ms": self.get_percentile(50),
                    "p95_ms": self.get_percentile(95),
                    "p99_ms": self.get_percentile(99),
                    "samples": len(self._latencies),
                },
            }

    def reset(self):
        """Reseta contadores"""
        with self._lock:
            self._request_count = 0
            self._error_count = 0
            self._status_counts.clear()
            self._latencies.clear()


# Singleton global
metrics = MetricsCollector()
