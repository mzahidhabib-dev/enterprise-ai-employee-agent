# src/observability/metrics.py
"""
Prometheus Metrics Exporter.

Defines custom telemetry metrics (counters, gauges, histograms) for the AI Agent.
These metrics are exposed via FastAPI and scraped by Prometheus to populate
Grafana dashboards for real-time observability.
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# 1. Pipeline Metrics
emails_processed = Counter(
    "emails_processed_total", 
    "Total number of emails processed", 
    ["agent_id"]
)

agent_latency = Histogram(
    "agent_run_seconds", 
    "Duration of a single agent graph execution in seconds", 
    ["agent_id"]
)

# 2. LLM / Gemini Metrics
gemini_calls = Counter(
    "gemini_calls_total", 
    "Total Gemini API calls made", 
    ["node_name", "agent_id"]
)

gemini_cost = Gauge(
    "gemini_cost_usd_total", 
    "Cumulative estimated Gemini cost in USD", 
    ["agent_id"]
)

# 3. Security & Gateway Metrics
pii_detections = Counter(
    "pii_detections_total", 
    "Total number of PII entities found and redacted", 
    ["entity_type"]
)

injection_attempts = Counter(
    "injection_attempts_total", 
    "Total number of prompt injection attempts detected and blocked"
)

def get_prometheus_metrics() -> bytes:
    """Returns the latest metric data in the Prometheus text format."""
    return generate_latest()
