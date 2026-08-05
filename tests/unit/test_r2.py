from datetime import UTC, datetime

import httpx
import pytest

from app.services.r2 import R2StorageClient, StorageError


class FakeAsyncClient:
    status = 200
    request: tuple[str, bytes, dict[str, str]] | None = None

    def __init__(self, **kwargs: object) -> None:
        assert kwargs["follow_redirects"] is False

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def put(self, url: str, *, content: bytes, headers: dict[str, str]) -> httpx.Response:
        self.__class__.request = (url, content, headers)
        return httpx.Response(self.status)


async def test_put_private_signs_r2_request(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.status = 200
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    client = R2StorageClient("https://account.r2.cloudflarestorage.com", "private", "key", "secret")
    await client.put_private("requests/id/file.pdf", b"data", "application/pdf")
    assert FakeAsyncClient.request is not None
    url, data, headers = FakeAsyncClient.request
    assert url.endswith("/private/requests/id/file.pdf")
    assert data == b"data"
    assert headers["authorization"].startswith("AWS4-HMAC-SHA256 Credential=key/")
    assert headers["x-amz-content-sha256"]


async def test_put_private_raises_on_r2_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.status = 403
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    client = R2StorageClient("https://account.r2.cloudflarestorage.com", "private", "key", "secret")
    with pytest.raises(StorageError, match="403"):
        await client.put_private("requests/id/file.pdf", b"data", "application/pdf")


def test_presigned_get_is_scoped_and_short_lived() -> None:
    client = R2StorageClient("https://account.r2.cloudflarestorage.com", "private", "key", "secret")
    url = client.presign_get("requests/a file.pdf", 600, datetime(2026, 8, 4, 12, 0, tzinfo=UTC))
    assert "/private/requests/a%20file.pdf?" in url
    assert "X-Amz-Expires=600" in url
    assert "X-Amz-Signature=" in url
    assert "secret" not in url
