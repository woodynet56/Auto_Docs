import hashlib
import hmac

from app.core.security import verify_meta_signature


def test_meta_signature_accepts_authentic_body() -> None:
    body = b'{"synthetic":true}'
    signature = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert verify_meta_signature(body, signature, "test-secret")


def test_meta_signature_rejects_missing_malformed_and_modified_body() -> None:
    assert not verify_meta_signature(b"{}", None, "secret")
    assert not verify_meta_signature(b"{}", "sha1=bad", "secret")
    assert not verify_meta_signature(b"{}", "sha256=short", "secret")
    valid = "sha256=" + hmac.new(b"secret", b"{}", hashlib.sha256).hexdigest()
    assert not verify_meta_signature(b'{"changed":true}', valid, "secret")
