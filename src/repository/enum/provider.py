from enum import Enum


class Provider(str, Enum):
    """Платёжные провайдеры. Значение совпадает с `name` плагина в PaymentExecute.

    Нативный PG enum: добавление провайдера = новый член + миграция
    (ALTER TYPE ... ADD VALUE)."""

    MOCK = "mock"


DEFAULT_PROVIDER: Provider = Provider.MOCK
