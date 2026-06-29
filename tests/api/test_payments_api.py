"""API: POST /api/v1/payments (202) и GET /api/v1/payments/{id} — позитив/негатив,
auth (X-API-Key), обязательный Idempotency-Key, валидация, идемпотентность."""
from sqlalchemy import func, select

from infrastructure.Persistence.orm import PaymentORM

_AUTH = {"X-API-Key": "test-key"}
_BODY = {
    "amount": "199.90",
    "currency": "RUB",
    "description": "Подписка",
    "metadata": {"user_id": 7},
    "webhook_url": "https://wh.test/hook",
}


async def test_create_payment_returns_202(api_client, db):
    resp = await api_client.post(
        "/api/v1/payments",
        json=_BODY,
        headers={**_AUTH, "Idempotency-Key": "api-ok"},
    )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert "payment_id" in data and "created_at" in data
    count = (
        await db.execute(select(func.count()).select_from(PaymentORM))
    ).scalar_one()
    assert count == 1


async def test_create_payment_without_api_key_is_401(api_client):
    resp = await api_client.post(
        "/api/v1/payments", json=_BODY, headers={"Idempotency-Key": "no-key"}
    )
    assert resp.status_code == 401


async def test_create_payment_without_idempotency_key_is_422(api_client):
    resp = await api_client.post("/api/v1/payments", json=_BODY, headers=_AUTH)
    assert resp.status_code == 422


async def test_create_payment_invalid_amount_is_422(api_client):
    resp = await api_client.post(
        "/api/v1/payments",
        json={**_BODY, "amount": "0"},
        headers={**_AUTH, "Idempotency-Key": "bad-amount"},
    )
    assert resp.status_code == 422


async def test_create_payment_invalid_currency_is_422(api_client):
    resp = await api_client.post(
        "/api/v1/payments",
        json={**_BODY, "currency": "GBP"},
        headers={**_AUTH, "Idempotency-Key": "bad-cur"},
    )
    assert resp.status_code == 422


async def test_create_payment_idempotent_returns_same_id(api_client, db):
    headers = {**_AUTH, "Idempotency-Key": "api-dup"}
    first = await api_client.post("/api/v1/payments", json=_BODY, headers=headers)
    second = await api_client.post("/api/v1/payments", json=_BODY, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["payment_id"] == second.json()["payment_id"]
    count = (
        await db.execute(select(func.count()).select_from(PaymentORM))
    ).scalar_one()
    assert count == 1


async def test_get_payment_returns_details(api_client):
    created = await api_client.post(
        "/api/v1/payments",
        json=_BODY,
        headers={**_AUTH, "Idempotency-Key": "api-get"},
    )
    payment_id = created.json()["payment_id"]

    resp = await api_client.get(f"/api/v1/payments/{payment_id}", headers=_AUTH)

    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_id"] == payment_id
    assert data["amount"] == "199.90"
    assert data["currency"] == "RUB"
    assert data["metadata"] == {"user_id": 7}
    assert data["status"] == "pending"


async def test_get_payment_not_found_is_404(api_client):
    resp = await api_client.get(
        "/api/v1/payments/33333333-3333-3333-3333-333333333333", headers=_AUTH
    )
    assert resp.status_code == 404


async def test_get_payment_without_api_key_is_401(api_client):
    resp = await api_client.get(
        "/api/v1/payments/33333333-3333-3333-3333-333333333333"
    )
    assert resp.status_code == 401
