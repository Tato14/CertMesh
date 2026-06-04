"""Microsoft Foundry wiring: model backend + observability."""

from .client import ModelBackend, ModelUnavailable, get_model_backend
from .tracing import SpanRecord, Tracer

__all__ = ["ModelBackend", "ModelUnavailable", "get_model_backend", "SpanRecord", "Tracer"]
