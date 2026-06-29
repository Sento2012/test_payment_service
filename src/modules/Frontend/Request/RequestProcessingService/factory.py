from fastapi import APIRouter


class RequestProcessingServiceFactory:
    """Собирает API-роутер(ы) сервиса обработки входящих запросов."""

    def create_router(self) -> APIRouter:
        # ленивый импорт: routes тянет di.container (get_container), а контейнер
        # тянет эту фабрику — отложенный импорт разрывает цикл на этапе загрузки.
        from modules.Frontend.Request.RequestProcessingService.routes import payments

        return payments.router
