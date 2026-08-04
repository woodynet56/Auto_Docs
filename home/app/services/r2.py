"""Minimal private Cloudflare R2 client using AWS Signature Version 4."""

import hashlib
import hmac
from datetime import UTC, datetime
from urllib.parse import quote, urlencode, urlparse

import httpx


class StorageError(RuntimeError):
    """Raised when private object storage rejects an operation."""


class R2StorageClient:
    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        timeout_seconds: int = 20,
    ) -> None:
        self._endpoint = endpoint_url.rstrip("/")
        self._bucket = bucket
        self._access_key = access_key
        self._secret_key = secret_key
        self._timeout = timeout_seconds

    async def put_private(self, key: str, data: bytes, mime_type: str) -> None:
        now = datetime.now(UTC)
        parsed = urlparse(self._endpoint)
        path = f"/{quote(self._bucket, safe='')}/{quote(key, safe='/')}"
        payload_hash = hashlib.sha256(data).hexdigest()
        timestamp = now.strftime("%Y%m%dT%H%M%SZ")
        date = now.strftime("%Y%m%d")
        headers = {
            "content-type": mime_type,
            "host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": timestamp,
        }
        canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in sorted(headers))
        signed_headers = ";".join(sorted(headers))
        canonical_request = "\n".join(
            ["PUT", path, "", canonical_headers, signed_headers, payload_hash]
        )
        scope = f"{date}/auto/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                timestamp,
                scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        signing_key = self._signing_key(date)
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        headers["authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self._access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
            response = await client.put(f"{self._endpoint}{path}", content=data, headers=headers)
        if response.status_code not in {200, 201}:
            raise StorageError(f"R2 rejected upload with status {response.status_code}")

    async def get_private(self, key: str, maximum_bytes: int) -> bytes:
        """Fetch an object server-side; the signed URL is never returned to a client."""
        url = self.presign_get(key, 60)
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
            response = await client.get(url)
        if response.status_code != 200:
            raise StorageError(f"R2 rejected download with status {response.status_code}")
        if len(response.content) > maximum_bytes:
            raise StorageError("R2 object exceeds configured maximum")
        return response.content

    def _signing_key(self, date: str) -> bytes:
        key_date = hmac.new(
            f"AWS4{self._secret_key}".encode(), date.encode(), hashlib.sha256
        ).digest()
        key_region = hmac.new(key_date, b"auto", hashlib.sha256).digest()
        key_service = hmac.new(key_region, b"s3", hashlib.sha256).digest()
        return hmac.new(key_service, b"aws4_request", hashlib.sha256).digest()

    def presign_get(self, key: str, expires_seconds: int, now: datetime | None = None) -> str:
        """Create a short-lived GET URL without exposing R2 credentials."""
        instant = now or datetime.now(UTC)
        parsed = urlparse(self._endpoint)
        path = f"/{quote(self._bucket, safe='')}/{quote(key, safe='/')}"
        timestamp = instant.strftime("%Y%m%dT%H%M%SZ")
        date = instant.strftime("%Y%m%d")
        scope = f"{date}/auto/s3/aws4_request"
        params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self._access_key}/{scope}",
            "X-Amz-Date": timestamp,
            "X-Amz-Expires": str(expires_seconds),
            "X-Amz-SignedHeaders": "host",
        }
        query = urlencode(sorted(params.items()), quote_via=quote)
        canonical = "\n".join(
            ["GET", path, query, f"host:{parsed.netloc}\n", "host", "UNSIGNED-PAYLOAD"]
        )
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                timestamp,
                scope,
                hashlib.sha256(canonical.encode()).hexdigest(),
            ]
        )
        signature = hmac.new(
            self._signing_key(date), string_to_sign.encode(), hashlib.sha256
        ).hexdigest()
        return f"{self._endpoint}{path}?{query}&X-Amz-Signature={signature}"
