import httpx
import pytest

from app.services.whatsapp import MetaWhatsAppClient, WhatsAppDeliveryError


class FakeResponse:
    def __init__(self, data: dict[str, object], fail: bool = False) -> None:
        self._data = data
        self._fail = fail

    def raise_for_status(self) -> None:
        if self._fail:
            request = httpx.Request("POST", "https://example.test")
            response = httpx.Response(400, request=request)
            raise httpx.HTTPStatusError("bad", request=request, response=response)

    def json(self) -> dict[str, object]:
        return self._data


class FakeAsyncClient:
    responses: list[object] = []
    payload: dict[str, object] = {}

    def __init__(self, timeout: int) -> None:
        assert timeout == 3

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(
        self, url: str, *, headers: dict[str, str], json: dict[str, object]
    ) -> FakeResponse:
        assert url.endswith("/v23.0/phone-id/messages")
        assert headers["Authorization"].startswith("Bearer ")
        self.__class__.payload = json
        result = self.__class__.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, FakeResponse)
        return result


def client(max_retries: int = 1) -> MetaWhatsAppClient:
    return MetaWhatsAppClient(
        api_version="v23.0",
        phone_number_id="phone-id",
        access_token="synthetic-token",
        timeout_seconds=3,
        max_retries=max_retries,
    )


async def test_meta_client_returns_provider_id_and_strips_plus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.responses = [FakeResponse({"messages": [{"id": "wamid.OUT"}]})]
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    assert await client().send_text("+525500000001", "Masked only") == "wamid.OUT"
    assert FakeAsyncClient.payload["to"] == "525500000001"


async def test_meta_client_retries_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "https://example.test")
    FakeAsyncClient.responses = [
        httpx.ReadTimeout("timeout", request=request),
        FakeResponse({"messages": [{"id": "wamid.RETRY"}]}),
    ]
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    assert await client().send_text("+525500000001", "Retry") == "wamid.RETRY"


@pytest.mark.parametrize(
    "response",
    [FakeResponse({}, fail=True), FakeResponse({"messages": []}), FakeResponse({"messages": [{}]})],
)
async def test_meta_client_converts_external_failures(
    monkeypatch: pytest.MonkeyPatch, response: FakeResponse
) -> None:
    FakeAsyncClient.responses = [response]
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    with pytest.raises(WhatsAppDeliveryError):
        await client(max_retries=0).send_text("+525500000001", "No secret")


def test_meta_client_requires_configuration() -> None:
    with pytest.raises(RuntimeError, match="not configured"):
        MetaWhatsAppClient(
            api_version="v23.0",
            phone_number_id="",
            access_token="",
            timeout_seconds=3,
            max_retries=0,
        )
