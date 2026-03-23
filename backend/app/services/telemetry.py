"""
Telemetry Service - Prometheus metrics for Bridge Twin System.

Metrics:
- Agent-level: latency, CPU, memory, decisions
- System-level: swarm latency (P50/P99), queue depth
- Health: heartbeat, failure detection, recovery time
"""
import logging
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# Agent-level metrics
agent_latency_seconds = Histogram(
    "agent_latency_seconds",
    "Agent processing time in seconds",
    ["agent_id", "task_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

agent_decisions_total = Counter(
    "agent_decisions_total",
    "Total decisions made by agent",
    ["agent_id", "decision_type", "outcome"],
)

agent_cpu_percent = Gauge(
    "agent_cpu_percent",
    "Agent CPU utilization percentage",
    ["agent_id"],
)

agent_memory_mb = Gauge(
    "agent_memory_mb",
    "Agent memory consumption in MB",
    ["agent_id"],
)

agent_heartbeat_seconds = Gauge(
    "agent_heartbeat_seconds",
    "Seconds since last agent heartbeat",
    ["agent_id"],
)

# Swarm-level metrics
swarm_latency_p50_seconds = Gauge(
    "swarm_latency_p50_seconds",
    "P50 inter-agent latency",
)

swarm_latency_p99_seconds = Gauge(
    "swarm_latency_p99_seconds",
    "P99 inter-agent latency",
)

message_queue_depth = Gauge(
    "message_queue_depth",
    "Number of pending messages in queue",
    ["channel"],
)

task_queue_wait_seconds = Gauge(
    "task_queue_wait_seconds",
    "Mission queue wait time in seconds",
    ["mission_type"],
)

# Health metrics
swarm_health_score = Gauge(
    "swarm_health_score",
    "Overall swarm health score (0-1)",
)

drift_detection_score = Gauge(
    "drift_detection_score",
    "Current drift detection score",
    ["agent_id"],
)

failure_detection_seconds = Gauge(
    "failure_detection_seconds",
    "Time to detect agent failure",
)

recovery_time_seconds = Gauge(
    "recovery_time_seconds",
    "Time to recover from failure",
)

# System metrics
active_twins = Gauge(
    "active_twins",
    "Number of active twin agents",
)

state_version = Gauge(
    "state_version",
    "Current state version",
)

entropy_score = Gauge(
    "entropy_score",
    "System entropy score",
)

# Execution gate metrics
execution_tasks_total = Counter(
    "execution_tasks_total",
    "Total tasks submitted to execution gate",
    ["stage"],
)

execution_rejection_rate = Gauge(
    "execution_rejection_rate",
    "Rate of tasks rejected by execution gate",
)


class TelemetryService:
    """Centralized telemetry for Bridge Twin System."""

    def __init__(self, port: int = 9090):
        self.port = port
        self._start_server()

    def _start_server(self) -> None:
        """Start Prometheus metrics HTTP server."""
        try:
            start_http_server(self.port)
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except OSError as e:
            logger.warning(f"Could not start metrics server on port {self.port}: {e}")

    def record_agent_latency(
        self, agent_id: str, task_type: str, latency_ms: float
    ) -> None:
        """Record agent processing latency."""
        agent_latency_seconds.labels(agent_id=agent_id, task_type=task_type).observe(
            latency_ms / 1000.0
        )

    def record_agent_decision(
        self, agent_id: str, decision_type: str, outcome: str
    ) -> None:
        """Record agent decision."""
        agent_decisions_total.labels(
            agent_id=agent_id, decision_type=decision_type, outcome=outcome
        ).inc()

    def update_agent_resources(
        self, agent_id: str, cpu_percent: float, memory_mb: float
    ) -> None:
        """Update agent resource usage."""
        agent_cpu_percent.labels(agent_id=agent_id).set(cpu_percent)
        agent_memory_mb.labels(agent_id=agent_id).set(memory_mb)

    def record_heartbeat(self, agent_id: str) -> None:
        """Record agent heartbeat."""
        agent_heartbeat_seconds.labels(agent_id=agent_id).set(0)

    def update_swarm_latency(self, p50_ms: float, p99_ms: float) -> None:
        """Update swarm latency metrics."""
        swarm_latency_p50_seconds.set(p50_ms / 1000.0)
        swarm_latency_p99_seconds.set(p99_ms / 1000.0)

    def update_queue_depth(self, channel: str, depth: int) -> None:
        """Update message queue depth."""
        message_queue_depth.labels(channel=channel).set(depth)

    def update_task_wait_time(self, mission_type: str, wait_seconds: float) -> None:
        """Update task queue wait time."""
        task_queue_wait_seconds.labels(mission_type=mission_type).set(wait_seconds)

    def update_health_score(self, score: float) -> None:
        """Update overall swarm health score."""
        swarm_health_score.set(score)

    def record_drift(self, agent_id: str, score: float) -> None:
        """Record drift detection score."""
        drift_detection_score.labels(agent_id=agent_id).set(score)

    def record_failure_detection_time(self, seconds: float) -> None:
        """Record time to detect failure."""
        failure_detection_seconds.set(seconds)

    def record_recovery_time(self, seconds: float) -> None:
        """Record recovery time."""
        recovery_time_seconds.set(seconds)

    def update_active_twins(self, count: int) -> None:
        """Update active twins count."""
        active_twins.set(count)

    def update_state_version(self, version: int) -> None:
        """Update state version."""
        state_version.set(version)

    def update_entropy(self, score: float) -> None:
        """Update entropy score."""
        entropy_score.set(score)

    def record_execution_task(self, stage: str) -> None:
        """Record execution gate task submission."""
        execution_tasks_total.labels(stage=stage).inc()

    def update_execution_rejection_rate(self, rate: float) -> None:
        """Update execution rejection rate."""
        execution_rejection_rate.set(rate)


# Global instance
_telemetry: Optional[TelemetryService] = None


def get_telemetry() -> TelemetryService:
    """Get or create global telemetry instance."""
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryService()
    return _telemetry
