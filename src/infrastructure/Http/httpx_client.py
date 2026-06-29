import httpx

from config.settings import get_settings
from shared.Port import HttpClientInterface


class HttpxClient(HttpClientInterface):
    """Реализация HTTP-клиента поверх httpx."""

    def __init__(self, timeout: float | None = None) -> None:
        self._timeout = (
            timeout if timeout is not None else get_settings().webhook.timeout
        )

    async def post(self, url: str, payload: dict) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()  # не-2xx -> HTTPStatusError -> retry
