import json
import logging
import traceback
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import perf_counter

from fastapi import Request, Response

_LOG_FIELDS = (
    "method",
    "path",
    "status_code",
    "duration_ms",
    "exception_type",
)

logger = logging.getLogger("budget_inator.http")


class JsonFormatter(logging.Formatter):
    """Format backend request logs as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["stack_trace"] = "".join(traceback.format_tb(record.exc_info[2]))

        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure the Budget-inator HTTP logger once per process."""
    if not any(
        isinstance(handler.formatter, JsonFormatter) for handler in logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    logger.setLevel(logging.INFO)
    logger.propagate = False
    logging.getLogger("uvicorn.access").disabled = True


async def log_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log request completion or failure without recording user-supplied data."""
    started_at = perf_counter()
    context = {
        "method": request.method,
        "path": request.url.path,
    }

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception(
            "request_failed",
            extra={
                **context,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                "exception_type": type(exc).__name__,
            },
        )
        raise

    logger.info(
        "request_completed",
        extra={
            **context,
            "status_code": response.status_code,
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )
    return response


configure_logging()
