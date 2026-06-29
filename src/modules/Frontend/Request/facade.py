from fastapi import APIRouter

from modules.Frontend.Request.RequestProcessingService.facade import (
    RequestProcessingServiceFacade,
)


class RequestFacade:
    """Публичный API frontend-модуля Request. Только проксирует в сервис обработки
    запросов (собирается в DI). Сами обработчики — в RequestProcessingService/routes.
    """

    def __init__(
        self, request_processing_service: RequestProcessingServiceFacade
    ) -> None:
        self._request_processing_service = request_processing_service

    def router(self) -> APIRouter:
        return self._request_processing_service.router()
