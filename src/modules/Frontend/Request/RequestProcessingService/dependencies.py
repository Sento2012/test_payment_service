from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from config.settings import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Статическая аутентификация по X-API-Key для всех эндпоинтов."""
    if not api_key or api_key != get_settings().api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )
