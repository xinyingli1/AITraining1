import pytest
from tools.pii import redact_pii
from tools.telemetry import PiiRedactingSpanProcessor
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.util.types import Attributes

def test_redact_pii_emails():
    text = "Contact me at john.doe@example.com or jane_doe123@gmail.co.uk."
    redacted = redact_pii(text)
    assert "john.doe@example.com" not in redacted
    assert "jane_doe123@gmail.co.uk" not in redacted
    assert "[EMAIL_REDACTED]" in redacted


def test_redact_pii_phones():
    text = "Call +1-234-567-8901 or (123) 456-7890. Local: 1234567890."
    redacted = redact_pii(text)
    assert "+1-234-567-8901" not in redacted
    assert "(123) 456-7890" not in redacted
    assert "1234567890" not in redacted
    assert "[PHONE_REDACTED]" in redacted


def test_redact_pii_credit_cards():
    text = "My card is 1234-5678-1234-5678 or 1234567812345678."
    redacted = redact_pii(text)
    assert "1234-5678-1234-5678" not in redacted
    assert "1234567812345678" not in redacted
    assert "[CREDIT_CARD_REDACTED]" in redacted


def test_redact_pii_ssn():
    text = "SSN is 000-12-3456."
    redacted = redact_pii(text)
    assert "000-12-3456" not in redacted
    assert "[SSN_REDACTED]" in redacted


def test_pii_redacting_span_processor():
    # Mock a ReadableSpan with attributes
    class MockSpan(ReadableSpan):
        def __init__(self, attributes: Attributes):
            self._attributes = attributes

        @property
        def attributes(self) -> Attributes:
            return self._attributes

    # Create a span with PII in attributes
    span = MockSpan({
        "search.query": "recipes for john.doe@example.com",
        "payment.phone": "Call 123-456-7890",
        "payment.amount": 45.50,  # Non-string attribute
        "tags": ["email:john@example.com", "clean_tag"]  # List of strings
    })

    processor = PiiRedactingSpanProcessor()
    processor.on_end(span)

    # Verify redaction
    assert span.attributes["search.query"] == "recipes for [EMAIL_REDACTED]"
    assert span.attributes["payment.phone"] == "Call [PHONE_REDACTED]"
    assert span.attributes["payment.amount"] == 45.50
    assert span.attributes["tags"] == ["email:[EMAIL_REDACTED]", "clean_tag"]
