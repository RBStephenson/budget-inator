import asyncio
import json
import logging
import sys
from unittest.mock import Mock

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient

from app.logging_config import JsonFormatter, log_request, logger
from app.main import app


def test_structured_logger_replaces_uvicorn_access_log() -> None:
    assert logging.getLogger("uvicorn.access").disabled is True


def test_json_formatter_emits_structured_request_fields() -> None:
    record = logging.LogRecord(
        name="budget_inator.http",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 1.25

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "budget_inator.http"
    assert payload["message"] == "request_completed"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.25
    assert "timestamp" in payload


def test_json_formatter_emits_structured_exception_context() -> None:
    exception_message = "sensitive user input"
    try:
        raise RuntimeError(exception_message)
    except RuntimeError:
        record = logging.LogRecord(
            name="budget_inator.http",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request_failed",
            args=(),
            exc_info=sys.exc_info(),
        )
    record.exception_type = "RuntimeError"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "ERROR"
    assert payload["message"] == "request_failed"
    assert payload["exception_type"] == "RuntimeError"
    assert "test_logging_config.py" in payload["stack_trace"]
    assert exception_message not in payload["stack_trace"]


def test_app_logs_completed_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    info = Mock()
    monkeypatch.setattr(logger, "info", info)

    with TestClient(app) as client:
        response = client.get("/health?token=not-logged")

    assert response.status_code == 200
    info.assert_called_once()
    assert info.call_args.args == ("request_completed",)
    assert info.call_args.kwargs["extra"]["method"] == "GET"
    assert info.call_args.kwargs["extra"]["path"] == "/health"
    assert info.call_args.kwargs["extra"]["status_code"] == 200
    assert "token" not in str(info.call_args.kwargs["extra"])


def test_failed_request_logs_safe_error_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = Mock()
    monkeypatch.setattr(logger, "exception", error)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/explode",
            "query_string": b"password=not-logged",
            "headers": [],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "root_path": "",
        }
    )

    async def fail(_: Request) -> Response:
        raise RuntimeError("internal detail")

    with pytest.raises(RuntimeError, match="internal detail"):
        asyncio.run(log_request(request, fail))

    error.assert_called_once()
    assert error.call_args.args == ("request_failed",)
    assert error.call_args.kwargs["extra"]["method"] == "POST"
    assert error.call_args.kwargs["extra"]["path"] == "/explode"
    assert error.call_args.kwargs["extra"]["exception_type"] == "RuntimeError"
    assert "password" not in str(error.call_args.kwargs["extra"])
