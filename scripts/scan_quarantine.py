"""Process the malware quarantine queue once for a Render Cron Job."""

import asyncio

from app.core.config import get_settings
from app.db.session import session_factory
from app.services.automatic_delivery import AutomaticDeliveryService
from app.services.malware import ClamAVScanner, QuarantineService
from app.services.r2 import R2StorageClient
from app.services.whatsapp import MetaWhatsAppClient


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
        if settings.WA_PHONE_NUMBER_ID and settings.WA_ACCESS_TOKEN.get_secret_value():
            await AutomaticDeliveryService(
                session,
                R2StorageClient(
                    settings.R2_ENDPOINT_URL or "",
                    settings.R2_BUCKET_NAME or "",
                    settings.R2_ACCESS_KEY_ID.get_secret_value(),
                    settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
                ),
                MetaWhatsAppClient(
                    api_version=settings.WA_API_VERSION,
                    phone_number_id=settings.WA_PHONE_NUMBER_ID,
                    access_token=settings.WA_ACCESS_TOKEN.get_secret_value(),
                    timeout_seconds=settings.META_HTTP_TIMEOUT_SECONDS,
                    max_retries=settings.META_MAX_RETRIES,
                ),
                settings.DELIVERY_LINK_TTL_SECONDS,
            ).process_due()


if __name__ == "__main__":
    asyncio.run(main())
