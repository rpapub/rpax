"""Lake-level diagnostics and error collection for rpax.

Provides run-scoped error collection and lake-level diagnostic artifacts
for analysability and debugging support according to ADR-026 and ADR-027.
"""

from .error_collector import (
    ErrorCollector,
    ErrorContext,
    ErrorSeverity,
    RpaxError,
    ErrorSummary,
    create_error_collector
)

__all__ = [
    "ErrorCollector",
    "ErrorContext", 
    "ErrorSeverity",
    "RpaxError",
    "ErrorSummary",
    "create_error_collector"
]