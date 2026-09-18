"""In-process metrics/logs/traces stores for the simulated production service.

Simulated-environment note: this is a lightweight, real (not faked) in-memory
observability layer for a single-process demo service — not a claim that it
replaces a real APM stack. Data is genuinely recorded from real requests/queries.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from statistics import mean
from threading import Lock
from typing import Deque


@dataclass
class EndpointStats:
    count: int = 0
    error_count: int = 0
    durations_ms: list = field(default_factory=list)

    def record(self, duration_ms: float, is_error: bool) -> None:
        self.count += 1
        if is_error:
            self.error_count += 1
        self.durations_ms.append(duration_ms)
        if len(self.durations_ms) > 500:
            self.durations_ms.pop(0)

    def summary(self) -> dict:
        durations = sorted(self.durations_ms)
        p99 = durations[int(len(durations) * 0.99) - 1] if durations else 0.0
        return {
            "count": self.count,
            "error_count": self.error_count,
            "avg_latency_ms": round(mean(durations), 2) if durations else 0.0,
            "p99_latency_ms": round(p99, 2),
        }


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._by_endpoint: dict[str, EndpointStats] = {}

    def record(self, endpoint: str, duration_ms: float, is_error: bool) -> None:
        with self._lock:
            stats = self._by_endpoint.setdefault(endpoint, EndpointStats())
            stats.record(duration_ms, is_error)

    def snapshot(self) -> dict:
        with self._lock:
            total_count = sum(s.count for s in self._by_endpoint.values())
            total_errors = sum(s.error_count for s in self._by_endpoint.values())
            return {
                "request_count": total_count,
                "error_count": total_errors,
                "by_endpoint": {ep: s.summary() for ep, s in self._by_endpoint.items()},
            }


class LogStore:
    def __init__(self, maxlen: int = 200) -> None:
        self._lock = Lock()
        self._entries: Deque[dict] = deque(maxlen=maxlen)

    def add(self, entry: dict) -> None:
        with self._lock:
            self._entries.append(entry)

    def recent(self, limit: int = 50) -> list:
        with self._lock:
            return list(self._entries)[-limit:][::-1]


class TraceStore:
    def __init__(self, maxlen: int = 100) -> None:
        self._lock = Lock()
        self._traces: Deque[dict] = deque(maxlen=maxlen)

    def add(self, trace: dict) -> None:
        with self._lock:
            self._traces.append(trace)

    def recent(self, limit: int = 20) -> list:
        with self._lock:
            return list(self._traces)[-limit:][::-1]

    def get(self, trace_id: str) -> dict | None:
        with self._lock:
            for trace in self._traces:
                if trace["trace_id"] == trace_id:
                    return trace
        return None


class QueryStore:
    def __init__(self, maxlen: int = 200) -> None:
        self._lock = Lock()
        self._queries: Deque[dict] = deque(maxlen=maxlen)

    def add(self, query: dict) -> None:
        with self._lock:
            self._queries.append(query)

    def recent(self, limit: int = 20) -> list:
        with self._lock:
            return list(self._queries)[-limit:][::-1]

    def summary(self) -> dict:
        with self._lock:
            queries = list(self._queries)
        durations = [q["duration_ms"] for q in queries]
        return {
            "total_queries": len(queries),
            "avg_query_ms": round(mean(durations), 2) if durations else 0.0,
        }


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


metrics_store = MetricsStore()
log_store = LogStore()
trace_store = TraceStore()
query_store = QueryStore()
