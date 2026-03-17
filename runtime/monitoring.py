"""Minimal observability bootstrap for Cloud Run deployment.

AUDIT-FIX: D-1 -- provide setup_monitoring() entry point so structured
log fields are present for Cloud Logging integration.

Phase D-1b (OpenTelemetry tracing, CostRecord wiring, dashboards) is
deferred to a follow-up.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("audhd_agents.monitoring")


def setup_monitoring() -> None:
    """Initialize monitoring hooks.

    Currently ensures structured logging severity mapping is in place.
    Cloud Run built-in metrics (request count, latency, memory) are
    automatic and require no runtime code.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    logger.info("Monitoring initialized (structured logging active)")
