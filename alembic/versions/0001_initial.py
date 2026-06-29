"""Начальная схема: расширение pgvector + таблицы (привязка к user_id, §10).

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "allowed_users",
        sa.Column("telegram_id", sa.BigInteger(), primary_key=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("color_type", sa.String(), nullable=True),
        sa.Column("contrast", sa.String(), nullable=True),
        sa.Column("silhouette_json", sa.String(), nullable=True),
        sa.Column("sex", sa.String(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("lifestyle", sa.String(), nullable=True),
        sa.Column("dress_code", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
    )

    op.create_table(
        "wardrobe_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("material", sa.String(), nullable=True),
        sa.Column("seasonality", sa.String(), nullable=True),
        sa.Column("style", sa.String(), nullable=True),
        sa.Column("brand", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("photo_key", sa.String(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            index=True,
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("blob_key", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("photos")
    op.drop_table("wardrobe_items")
    op.drop_table("users")
    op.drop_table("allowed_users")
