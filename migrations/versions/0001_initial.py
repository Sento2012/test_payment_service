"""initial schema: payments + payment_outbox

Revision ID: 0001
Revises:
Create Date: 2026-06-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Нативные enum-типы создаём явно (create_type=False у колонок ниже).
payment_status = postgresql.ENUM(
    "pending", "succeeded", "failed", name="payment_status", create_type=False
)
currency = postgresql.ENUM("RUB", "USD", "EUR", name="currency", create_type=False)
provider = postgresql.ENUM("mock", name="provider", create_type=False)
outbox_status = postgresql.ENUM(
    "pending", "published", "failed", name="outbox_status", create_type=False
)
event_type = postgresql.ENUM("payments.new", name="event_type", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    payment_status.create(bind, checkfirst=True)
    currency.create(bind, checkfirst=True)
    provider.create(bind, checkfirst=True)
    outbox_status.create(bind, checkfirst=True)
    event_type.create(bind, checkfirst=True)

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", currency, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "meta",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            payment_status,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("provider", provider, server_default="mock", nullable=False),
        sa.Column("provider_ref", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "payment_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("routing_key", sa.String(64), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", outbox_status, server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name="fk_payment_outbox_payment_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_payment_outbox_pending",
        "payment_outbox",
        ["available_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_payment_outbox_payment_id", "payment_outbox", ["payment_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_payment_outbox_payment_id", table_name="payment_outbox")
    op.drop_index("ix_payment_outbox_pending", table_name="payment_outbox")
    op.drop_table("payment_outbox")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_table("payments")

    bind = op.get_bind()
    event_type.drop(bind, checkfirst=True)
    outbox_status.drop(bind, checkfirst=True)
    provider.drop(bind, checkfirst=True)
    currency.drop(bind, checkfirst=True)
    payment_status.drop(bind, checkfirst=True)
