from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from config.settings import get_settings
from di.container import get_container
from modules.Backend.Payment.PaymentCreate import PaymentCreator
from modules.Backend.Payment.PaymentRepository import PaymentRepositoryService

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Статическая аутентификация по X-API-Key для всех эндпоинтов."""
    if not api_key or api_key != get_settings().api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


# Провайдеры сервисов для роутов. Достаём из composition root, но через границу
# FastAPI (Depends), а не обращением к контейнеру внутри роута: зависимость видна в
# сигнатуре и подменяется в тестах через app.dependency_overrides.
def _payment_creator() -> PaymentCreator:
    return get_container().payment_creator()


def _payment_repository_service() -> PaymentRepositoryService:
    return get_container().payment_repository_service()


PaymentCreatorDep = Annotated[PaymentCreator, Depends(_payment_creator)]
PaymentRepositoryDep = Annotated[PaymentRepositoryService, Depends(_payment_repository_service)]
