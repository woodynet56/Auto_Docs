import httpx
import pytest

from app.services.meta_media import MediaDownloadError, MetaMediaClient


class FakeAsyncClient:
    responses: list[httpx.Response] = []

    def __init__(self, **kwargs: object) -> None:
        assert kwargs["follow_redirects"] is False

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        assert kwargs["headers"] == {"Authorization": "Bearer token"}
        return self.responses.pop(0)


async def test_downloads_only_from_meta_allowlisted_host(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.responses = [
        httpx.Response(200, json={"url": "https://lookaside.fbsbx.com/media/file"}),
        httpx.Response(200, content=b"%PDF-1.7"),
    ]
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    assert await MetaMediaClient("v23.0", "token", 100).download("media") == b"%PDF-1.7"


@pytest.mark.parametrize(
    "responses",
    [
        [httpx.Response(500)],
        [httpx.Response(200, json={"url": "https://evil.example/file"})],
        [
            httpx.Response(200, json={"url": "https://lookaside.fbsbx.com/media/file"}),
            httpx.Response(200, content=b"too-large"),
        ],
    ],
)
async def test_rejects_failed_untrusted_or_large_download(
    monkeypatch: pytest.MonkeyPatch, responses: list[httpx.Response]
) -> None:
    FakeAsyncClient.responses = list(responses)
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    with pytest.raises(MediaDownloadError):
        await MetaMediaClient("v23.0", "token", 2).download("media")
