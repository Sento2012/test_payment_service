"""Валидация входных параметров POST /api/v1/payments (422) и невалидный id в GET.

Проверяем, что кривой ввод отсекается на валидации (Pydantic/FastAPI) ДО бизнес-логики
и ничего не пишется в БД."""
import copy

import pytest
from sqlalchemy import func, select

from infrastructure.Persistence.orm import PaymentORM

_AUTH = {"X-API-Key": "test-key"}
_VALID = {
    "amount": "199.90",
    "currency": "RUB",
    "description": "d",
    "metadata": {"x": 1},
    "webhook_url": "https://wh.test/hook",
}


def _body(**changes) -> dict:
    body = copy.deepcopy(_VALID)
    body.update(changes)
    return body


def _without(key: str) -> dict:
    body = copy.deepcopy(_VALID)
    body.pop(key)
    return body


_INVALID_CASES = [
    ("amount_zero", _body(amount="0")),
    ("amount_negative", _body(amount="-1.00")),
    ("amount_too_many_decimals", _body(amount="1.999")),
    ("amount_too_many_digits", _body(amount="12345678901234567.89")),  # 19 цифр > 18
    ("amount_not_a_number", _body(amount="abc")),
    ("amount_missing", _without("amount")),
    ("currency_missing", _without("currency")),
    ("currency_unknown", _body(currency="GBP")),
    ("extra_field_forbidden", _body(foo="bar")),
    ("description_too_long", _body(description="x" * 1025)),
    ("webhook_url_too_long", _body(webhook_url="https://" + "a" * 2048)),
    ("metadata_wrong_type", _body(metadata="not-a-dict")),
    ("empty_body", {}),
    # SSRF: webhook_url только https и не приватный/служебный хост
    ("webhook_not_https", _body(webhook_url="http://example.com/hook")),
    ("webhook_localhost", _body(webhook_url="https://localhost/hook")),
    ("webhook_private_ip", _body(webhook_url="https://10.0.0.1/hook")),
    ("webhook_link_local_metadata", _body(webhook_url="https://169.254.169.254/latest")),
]


@pytest.mark.parametrize(
    "case_id, body", _INVALID_CASES, ids=[c[0] for c in _INVALID_CASES]
)
async def test_create_payment_invalid_body_is_422(api_client, db, case_id, body):
    resp = await api_client.post(
        "/api/v1/payments",
        json=body,
        headers={**_AUTH, "Idempotency-Key": f"val-{case_id}"},
    )

    assert resp.status_code == 422, f"{case_id}: ожидали 422, получили {resp.status_code}"
    count = (
        await db.execute(select(func.count()).select_from(PaymentORM))
    ).scalar_one()
    assert count == 0


async def test_get_payment_invalid_uuid_is_422(api_client):
    resp = await api_client.get("/api/v1/payments/not-a-uuid", headers=_AUTH)
    assert resp.status_code == 422
