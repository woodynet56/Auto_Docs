import json
import logging

from app.core.logging import JsonFormatter, _redact


def test_redaction_supports_nested_collections() -> None:
    value = [{"phone_number": "synthetic"}, ({"safe": "value"},)]
    assert _redact(value) == [{"phone_number": "[REDACTED]"}, ({"safe": "value"},)]


def test_formatter_redacts_sensitive_context() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "processed", (), None)
    record.context = {"request_id": "synthetic", "rfc": "TEST010101AAA", "token": "secret"}

    payload = json.loads(JsonFormatter().format(record))

    assert payload["context"]["request_id"] == "synthetic"
    assert payload["context"]["rfc"] == "[REDACTED]"
    assert payload["context"]["token"] == "[REDACTED]"
