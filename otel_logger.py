"""OpenTelemetry-aware logger wrapper for plain Python logging.

This module exposes a lightweight logger adapter that behaves like a normal Python
logger while also optionally creating OpenTelemetry spans and injecting trace
context into log output.

The main benefit is that application code can remain simple and call normal
logging methods such as ``logger.info(...)`` and ``logger.error(...)``.

Example usage:

    from otel_logger import get_logger

    logger = get_logger("diceroller")
    logger.info("Starting dice roll")

    result = 6
    logger.info(
        "Rolled dice value %s",
        result,
        span_name="roll",
        span_attributes={"roll.value": result},
    )

    try:
        raise ValueError("bad dice")
    except Exception:
        logger.exception("Dice roll failed")

Use cases:

- simple logging with no trace/span context
- logging with a nested OpenTelemetry span attached to a log event
- logging with automatic trace/span context propagation across the current span
- error logging with ``logger.exception(...)`` and automatic ``exc_info``

The logger can also be created with ``auto_start_spans=True``, which means every
log message will automatically start a span named after the logging level
(e.g. ``info``, ``error``) if no explicit ``span_name`` is provided.
"""

import logging
from typing import Any

from opentelemetry import trace

TRACE_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s trace=%(trace_id)s span=%(span_id)s %(message)s"
)


class TraceContextFilter(logging.Filter):
    """Attach OpenTelemetry trace and span ids to each log record.

    This filter reads the current active span from OpenTelemetry and adds two
    record attributes:

    - ``trace_id``: current trace identifier or empty string
    - ``span_id``: current span identifier or empty string

    The values are formatted as lower-case hex strings so they can be rendered
    consistently in log output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx and ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        else:
            record.trace_id = ""
            record.span_id = ""
        return True


class TracedLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that optionally starts OpenTelemetry spans for log calls.

    ``TracedLoggerAdapter`` wraps a standard ``logging.Logger`` and provides the
    same public methods (``debug()``, ``info()``, ``warning()``, ``error()``,
    ``critical()``, and ``exception()``) while allowing an optional ``span_name``
    and ``span_attributes`` per call.

    When a span is started, the log call executes within that span and the
    active span context is automatically attached to the log record via the
    ``TraceContextFilter``.
    """

    def __init__(self, logger: logging.Logger, auto_start_spans: bool = False) -> None:
        super().__init__(logger, {})
        self._tracer = trace.get_tracer(logger.name)
        self._auto_start_spans = auto_start_spans

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Inject trace/span context into log record extra data."""
        extra = kwargs.get("extra")
        if extra is None:
            extra = {}

        span = trace.get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx and ctx.is_valid:
            extra["trace_id"] = format(ctx.trace_id, "032x")
            extra["span_id"] = format(ctx.span_id, "016x")
        else:
            extra.setdefault("trace_id", "")
            extra.setdefault("span_id", "")

        kwargs["extra"] = extra
        return msg, kwargs

    def _log_with_optional_span(
        self,
        level: int,
        msg: str,
        *args: Any,
        span_name: str | None = None,
        span_attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log with an optional OpenTelemetry span.

        If ``span_name`` is provided, or if ``auto_start_spans`` was enabled on
        logger creation, a span is started around the log call.
        """
        if span_name or self._auto_start_spans:
            if span_name is None:
                span_name = logging.getLevelName(level).lower()
            if span_attributes is None:
                span_attributes = {}
            with self._tracer.start_as_current_span(
                span_name, attributes=span_attributes
            ):
                super().log(level, msg, *args, **kwargs)
        else:
            super().log(level, msg, *args, **kwargs)

    def debug(
        self,
        msg: str,
        *args: Any,
        span_name: str | None = None,
        span_attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._log_with_optional_span(
            logging.DEBUG,
            msg,
            *args,
            span_name=span_name,
            span_attributes=span_attributes,
            **kwargs,
        )

    def info(
        self,
        msg: str,
        *args: Any,
        span_name: str | None = None,
        span_attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._log_with_optional_span(
            logging.INFO,
            msg,
            *args,
            span_name=span_name,
            span_attributes=span_attributes,
            **kwargs,
        )

    def warning(
        self,
        msg: str,
        *args: Any,
        span_name: str | None = None,
        span_attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._log_with_optional_span(
            logging.WARNING,
            msg,
            *args,
            span_name=span_name,
            span_attributes=span_attributes,
            **kwargs,
        )

    def error(
        self,
        msg: str,
        *args: Any,
        span_name: str | None = None,
        span_attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._log_with_optional_span(
            logging.ERROR,
            msg,
            *args,
            span_name=span_name,
            span_attributes=span_attributes,
            **kwargs,
        )

    def critical(
        self,
        msg: str,
        *args: Any,
        span_name: str | None = None,
        span_attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._log_with_optional_span(
            logging.CRITICAL,
            msg,
            *args,
            span_name=span_name,
            span_attributes=span_attributes,
            **kwargs,
        )

    def exception(
        self,
        msg: str,
        *args: Any,
        span_name: str | None = None,
        span_attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log an exception and include traceback information."""
        kwargs.setdefault("exc_info", True)
        self._log_with_optional_span(
            logging.ERROR,
            msg,
            *args,
            span_name=span_name,
            span_attributes=span_attributes,
            **kwargs,
        )


def get_logger(
    name: str = "roll-dice", level: int = logging.INFO, auto_start_spans: bool = False
) -> TracedLoggerAdapter:
    """Create and return an OpenTelemetry-capable logger adapter.

    Args:
        name: logger name, passed through to Python's ``logging.getLogger``.
        level: logging level threshold.
        auto_start_spans: if True, every log method call starts a span named after
            the logging level when ``span_name`` is not explicitly provided.

    Returns:
        A ``TracedLoggerAdapter`` instance with trace context injection enabled.

    Example:

        logger = get_logger("diceroller")
        logger.info("Started")

        # start a span for this operation only when logging
        logger.info(
            "Rolled dice",
            span_name="roll",
            span_attributes={"roll.value": 4},
        )

        try:
            raise RuntimeError("oops")
        except Exception:
            logger.exception("Failure during operation")

        # automatic span creation for every log statement
        automatic_logger = get_logger("auto-diceroller", auto_start_spans=True)
        automatic_logger.warning("This log starts a warning span automatically")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(TRACE_FORMAT))
        logger.addHandler(handler)

    if not any(isinstance(item, TraceContextFilter) for item in logger.filters):
        logger.addFilter(TraceContextFilter())

    return TracedLoggerAdapter(logger, auto_start_spans=auto_start_spans)
