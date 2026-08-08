"""Security primitives for authenticating Meta webhook requests."""

import hashlib
import hmac


def verify_meta_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Validate ``X-Hub-Signature-256`` without timing-leaky comparison."""
    if not signature_header or not app_secret or not signature_header.startswith("sha256="):
        return False
    supplied = signature_header.removeprefix("sha256=")
    if len(supplied) != 64:
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)
