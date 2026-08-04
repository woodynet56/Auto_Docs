"""Minimal Meta Graph API client with bounded timeout and retries."""

import asyncio
from typing import Protocol

import httpx


class WhatsAppDeliveryError(RuntimeError):
    pass


class WhatsAppSender(Protocol):
    async def send_text(self, recipient: str, text: str) -> str: ...


class MetaWhatsAppClient:
    def __init__(
        self,
        *,
        api_version: str,
        phone_number_id: str,
        access_token: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> None:
        if not phone_number_id or not access_token:
            raise RuntimeError("Meta WhatsApp delivery is not configured")
        self._url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        self._token = access_token
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    async def send_text(self, recipient: str, text: str) -> str:
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient.removeprefix("+"),
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    response = await client.post(self._url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    message_id = data["messages"][0]["id"]
                    if not isinstance(message_id, str) or not message_id:
                        raise WhatsAppDeliveryError("Meta response did not include a message ID")
                    return message_id
                except (httpx.TimeoutException, httpx.NetworkError) as error:
                    if attempt == self._max_retries:
                        raise WhatsAppDeliveryError("Meta request failed") from error
                    await asyncio.sleep(0.25 * (2**attempt))
                except (
                    httpx.HTTPStatusError,
                    KeyError,
                    IndexError,
                    TypeError,
                    ValueError,
                ) as error:
                    raise WhatsAppDeliveryError("Meta rejected the request") from error
        raise WhatsAppDeliveryError("Meta request failed")
