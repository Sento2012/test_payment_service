from repository.entity.idempotency_record import IdempotencyRecord
from repository.payment_provider_idempotency_store_repository import PaymentProviderIdempotencyStoreRepository
from modules.Backend.Idempotency.PaymentProviderIdempotencyStoreRepository.Dto.idempotency_transfer import (
    IdempotencyKeyTransfer,
    IdempotencyRecordDraftTransfer,
)
from shared.Port.persistence import UnitOfWork


class PaymentProviderIdempotencyStoreRepositoryService:
    """Доступ к стору идемпотентности — единообразно через use_transaction(context).

    ВАЖНО: вызывающий (PaymentExecutor) передаёт ПУСТОЙ контекст → открывается СВОЯ
    короткая транзакция. Это намеренно: запись о charge должна коммититься независимо
    и пережить откат платёжной транзакции, иначе при краше между списанием и commit'ом
    статуса передоставка привела бы к двойному списанию. Контекст платежа сюда НЕ
    прокидывать (иначе enlisting в его tx сломает гарантию)."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        payment_provider_idempotency_store_repository: PaymentProviderIdempotencyStoreRepository,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._payment_provider_idempotency_store_repository = payment_provider_idempotency_store_repository

    async def find_record(
        self, idempotency_key_transfer: IdempotencyKeyTransfer
    ) -> IdempotencyRecord | None:
        async with self._unit_of_work.use_transaction(
            idempotency_key_transfer.context
        ) as session:
            return await self._payment_provider_idempotency_store_repository.find(
                session, idempotency_key_transfer.key
            )

    async def get_or_create_record(
        self, idempotency_record_draft_transfer: IdempotencyRecordDraftTransfer
    ) -> IdempotencyRecord:
        idempotency_record = IdempotencyRecord(
            key=idempotency_record_draft_transfer.key,
            value=idempotency_record_draft_transfer.value,
        )
        async with self._unit_of_work.use_transaction(
            idempotency_record_draft_transfer.context
        ) as session:
            return await self._payment_provider_idempotency_store_repository.get_or_create(
                session, idempotency_record
            )
