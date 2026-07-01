import re

# Regex patterns for common PII
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
# Covers formats like: +1-234-567-8901, (123) 456-7890, 123.456.7890, 1234567890
PHONE_PATTERN = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
# Covers 13 to 16 digit credit card numbers, with or without spaces/dashes
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
# US Social Security Numbers
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def redact_pii(text: str) -> str:
    """Redacts common PII (emails, phone numbers, credit cards, SSNs) from the text."""
    if not isinstance(text, str):
        return text

    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)
    text = CREDIT_CARD_PATTERN.sub("[CREDIT_CARD_REDACTED]", text)
    text = SSN_PATTERN.sub("[SSN_REDACTED]", text)
    return text
