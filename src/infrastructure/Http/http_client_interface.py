from abc import ABC, abstractmethod


class HttpClientInterface(ABC):
    """Порт для исходящих HTTP-запросов. Бизнес-слой зависит от абстракции, не от httpx."""

    @abstractmethod
    async def post(self, url: str, payload: dict) -> None:
        """POST с JSON-телом. Должен бросить исключение при ошибке доставки
        (сетевая ошибка / не-2xx ответ) — это сигнал для retry."""
        ...
