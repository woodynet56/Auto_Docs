"""Process the malware quarantine queue once for a Render Cron Job."""

import asyncio

from app.core.config import get_settings
from app.db.session import session_factory
from app.services.malware import ClamAVScanner, QuarantineService
from app.services.r2 import R2StorageClient


async def main() -> None:
    settings = get_settings()
    required = (
        settings.CLAMAV_HOST,
        settings.R2_ENDPOINT_URL,
        settings.R2_BUCKET_NAME,
        settings.R2_ACCESS_KEY_ID.get_secret_value(),
        settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
    )
    if not all(required):
        raise RuntimeError("quarantine worker configuration is incomplete")
    async with session_factory() as session:
        service = QuarantineService(
            session=session,
            storage=R2StorageClient(
                settings.R2_ENDPOINT_URL or "",
                settings.R2_BUCKET_NAME or "",
                settings.R2_ACCESS_KEY_ID.get_secret_value(),
                settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
            ),
            scanner=ClamAVScanner(
                settings.CLAMAV_HOST or "",
                settings.CLAMAV_PORT,
                settings.CLAMAV_TIMEOUT_SECONDS,
            ),
            maximum_bytes=settings.DOCUMENT_MAX_BYTES,
            maximum_attempts=settings.MALWARE_SCAN_MAX_ATTEMPTS,
        )
        await service.process_due()


if __name__ == "__main__":
    asyncio.run(main())
