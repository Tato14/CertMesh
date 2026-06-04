"""Per-agent observability.

Every orchestration step runs inside a span so the collaboration can be traced.
Locally we always record spans in-process (used for the ``duration_ms`` shown in
the orchestration trace and the dashboard). When Foundry/OTel is configured we
additionally bridge to OpenTelemetry so the same spans land in Foundry tracing /
Azure Monitor.

Agent Framework observability is enabled with ``configure_otel_providers()``;
GenAI spans are named ``invoke_agent``/``chat``/``execute_tool``. See
https://learn.microsoft.com/en-us/agent-framework/tutorials/observability
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from ..config import Config, load_config


@dataclass
class SpanRecord:
    name: str
    attributes: dict = field(default_factory=dict)
    duration_ms: float = 0.0


class Tracer:
    """Records spans in-process and optionally exports them via OpenTelemetry."""

    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self.spans: list[SpanRecord] = []
        self._otel = None
        self._setup_otel()

    def _setup_otel(self) -> None:
        cfg = self.config
        if not (cfg.appinsights_connection_string or cfg.trace_to_console):
            return
        try:  # pragma: no cover - exercised only with the optional SDKs present
            from agent_framework.observability import (  # type: ignore
                configure_otel_providers,
                get_tracer,
            )

            configure_otel_providers()
            self._otel = get_tracer("certmesh")
        except Exception:
            # Agent Framework not installed — try raw OTel, else stay local-only.
            try:  # pragma: no cover
                from opentelemetry import trace  # type: ignore

                self._otel = trace.get_tracer("certmesh")
            except Exception:
                self._otel = None

    @contextmanager
    def span(self, name: str, **attributes):
        start = time.perf_counter()
        otel_cm = None
        otel_span = None
        if self._otel is not None:  # pragma: no cover - needs OTel installed
            try:
                otel_cm = self._otel.start_as_current_span(name)
                otel_span = otel_cm.__enter__()
                for k, v in attributes.items():
                    otel_span.set_attribute(f"certmesh.{k}", str(v))
            except Exception:
                otel_cm = None
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            self.spans.append(SpanRecord(name=name, attributes=dict(attributes),
                                         duration_ms=duration_ms))
            if otel_cm is not None:  # pragma: no cover
                try:
                    otel_span.set_attribute("certmesh.duration_ms", duration_ms)
                    otel_cm.__exit__(None, None, None)
                except Exception:
                    pass

    def last_duration_ms(self, name: str) -> float | None:
        for rec in reversed(self.spans):
            if rec.name == name:
                return rec.duration_ms
        return None
