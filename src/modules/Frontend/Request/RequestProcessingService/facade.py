from fastapi import APIRouter

from modules.Frontend.Request.RequestProcessingService.factory import (
    RequestProcessingServiceFactory,
)


class RequestProcessingServiceFacade:
    def __init__(self, request_processing_service_factory: RequestProcessingServiceFactory) -> None:
        self._request_processing_service_factory = request_processing_service_factory

    def router(self) -> APIRouter:
        return self._request_processing_service_factory.create_router()
