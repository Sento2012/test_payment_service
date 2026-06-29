from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from di.container import get_container
from modules.Backend.Payment.PaymentCreate import PaymentDraftTransfer
from modules.Backend.Payment.PaymentRepository import PaymentFindTransfer
from modules.Frontend.Request.RequestProcessingService.dependencies import require_api_key
from modules.Frontend.Request.RequestProcessingService.schemas import (
    CreatePaymentRequest,
    PaymentCreatedResponse,
    PaymentResponse,
)
from repository.entity.payment import Payment

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(require_api_key)],
)

def _to_response(payment_transfer: Payment) -> PaymentResponse:
    return PaymentResponse(
        payment_id=payment_transfer.id,
        amount=payment_transfer.amount,
        currency=payment_transfer.currency,
        status=payment_transfer.status,
        description=payment_transfer.description,
        metadata=payment_transfer.meta,
        webhook_url=payment_transfer.webhook_url,
        provider=payment_transfer.provider,
        provider_ref=payment_transfer.provider_ref,
        failure_reason=payment_transfer.failure_reason,
        created_at=payment_transfer.created_at,
        processed_at=payment_transfer.processed_at,
        notified_at=payment_transfer.notified_at,
    )

@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PaymentCreatedResponse,
)
async def create_payment(
    body: CreatePaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> PaymentCreatedResponse:
    payment_draft_transfer = PaymentDraftTransfer(
        idempotency_key=idempotency_key,
        amount=body.amount,
        currency=body.currency,
        webhook_url=body.webhook_url,
        description=body.description,
        meta=body.metadata,
        provider=body.provider,
    )
    payment_transfer, _created = await get_container().payment_creator().create_payment(
        payment_draft_transfer
    )
    return PaymentCreatedResponse(
        payment_id=payment_transfer.id,
        status=payment_transfer.status,
        created_at=payment_transfer.created_at,
    )

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: UUID) -> PaymentResponse:
    payment_transfer = await get_container().payment_repository_service().find_payment(
        PaymentFindTransfer(payment_id=payment_id)
    )
    if payment_transfer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    return _to_response(payment_transfer)
