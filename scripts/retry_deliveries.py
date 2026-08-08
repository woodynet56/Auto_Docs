"""Run one bounded delivery-outbox retry cycle."""

import asyncio

from app.core.config import get_settings
from app.db.session import session_factory
from app.services.delivery import DeliveryService
from app.services.r2 import R2StorageClient
from app.services.whatsapp import MetaWhatsAppClient


async def main() -> int:
    settings = get_settings()
    required = (
        settings.R2_ENDPOINT_URL,
        settings.R2_BUCKET_NAME,
        settings.R2_ACCESS_KEY_ID.get_secret_value(),
        settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
        settings.WA_PHONE_NUMBER_ID,
        settings.WA_ACCESS_TOKEN.get_secret_value(),
        settings.WA_BUSINESS_PHONE_NUMBER,
    )
    if not all(required):
        raise RuntimeError("Delivery retry configuration is incomplete")
    async with session_factory() as session:
        service = DeliveryService(
            session=session,
            storage=R2StorageClient(
                settings.R2_ENDPOINT_URL or "",
                settings.R2_BUCKET_NAME or "",
                settings.R2_ACCESS_KEY_ID.get_secret_value(),
                settings.R2_SECRET_ACCESS_KEY.get_secret_value(),
            ),
            sender=MetaWhatsAppClient(
                api_version=settings.WA_API_VERSION,
                phone_number_id=settings.WA_PHONE_NUMBER_ID or "",
                access_token=settings.WA_ACCESS_TOKEN.get_secret_value(),
                timeout_seconds=settings.META_HTTP_TIMEOUT_SECONDS,
                max_retries=settings.META_MAX_RETRIES,
            ),
            business_phone=settings.WA_BUSINESS_PHONE_NUMBER or "",
            link_ttl_seconds=settings.DELIVERY_LINK_TTL_SECONDS,
            maximum_attempts=settings.DELIVERY_MAX_ATTEMPTS,
        )
        return await service.retry_due()


if __name__ == "__main__":
    asyncio.run(main())
