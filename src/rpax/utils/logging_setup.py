"""TRACE log level registration and logging configuration for rpax.

Registers a TRACE level (5, below DEBUG=10) with the Python logging framework
and patches logging.Logger with a .trace() method. Import this module once at
startup — rpax.__init__ does this automatically.
"""

import logging

TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def _trace(self: logging.Logger, msg: object, *args: object, **kwargs: object) -> None:
    if self.isEnabledFor(TRACE):
        self._log(TRACE, msg, args, **kwargs)  # type: ignore[attr-defined]


logging.Logger.trace = _trace  # type: ignore[attr-defined]

_LEVEL_MAP: dict[str, int] = {
    "trace": TRACE,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def configure_logging(level_str: str, fmt: str | None = None) -> None:
    """Configure root logger level and format.

    Idempotent: if the root logger already has handlers (e.g. pytest captured
    logging), only the level is updated — no duplicate handlers are added.

    Args:
        level_str: One of trace/debug/info/warn/error (case-insensitive).
        fmt: Optional log format string. Defaults to a compact rpax format.
    """
    level = _LEVEL_MAP.get(level_str.lower(), logging.INFO)
    root = logging.getLogger()

    if not root.handlers:
        logging.basicConfig(
            level=level,
            format=fmt or "%(levelname)-5s %(name)s: %(message)s",
        )
    else:
        root.setLevel(level)
