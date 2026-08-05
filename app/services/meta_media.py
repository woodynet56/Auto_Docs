"""Download authenticated media from Meta without following untrusted redirects."""

import httpx


class MediaDownloadError(RuntimeError):
    pass


class MetaMediaClient:
    def __init__(self, api_version: str, access_token: str, maximum_bytes: int) -> None:
        self._api_version = api_version
        self._access_token = access_token
        self._maximum_bytes = maximum_bytes

    async def download(self, media_id: str) -> bytes:
        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            metadata = await client.get(
                f"https://graph.facebook.com/{self._api_version}/{media_id}", headers=headers
            )
            if metadata.status_code != 200:
                raise MediaDownloadError("Meta media metadata request failed")
            url = metadata.json().get("url")
            if not isinstance(url, str) or not url.startswith("https://lookaside.fbsbx.com/"):
                raise MediaDownloadError("Meta returned an untrusted media URL")
            response = await client.get(url, headers=headers)
            if response.status_code != 200 or len(response.content) > self._maximum_bytes:
                raise MediaDownloadError("Meta media download failed or exceeded size limit")
            return response.content
