from alembic import op
import sqlalchemy as sa  # <-- missing import (needed for sa.Column etc.)


revision = "20251029_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sku", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.String),
        sa.Column("price_cents", sa.Integer, nullable=False),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column("category", sa.String),
        sa.Column("weight", sa.Numeric(10, 3), default=0),
        sa.Column("created_at", sa.DateTime)
    )

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("sku", sa.String, nullable=False, unique=True),
        sa.Column("price_cents", sa.Integer, nullable=False),
        sa.Column("attributes", sa.JSON),
        sa.Column("stock", sa.Integer, default=0)
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String),
        sa.Column("email", sa.String, unique=True),
        sa.Column("password_hash", sa.String)
    )

    op.create_table(
        "carts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id")),
        sa.Column("created_at", sa.DateTime),
        sa.Column("expires_at", sa.DateTime)
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cart_id", sa.Integer, sa.ForeignKey("carts.id")),
        sa.Column("sku", sa.String, nullable=False),
        sa.Column("qty", sa.Integer, nullable=False),
        sa.Column("price_snapshot", sa.Integer, nullable=False)
    )

    op.create_table(
        "inventory_reservations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sku", sa.String, nullable=False),
        sa.Column("qty", sa.Integer, nullable=False),
        sa.Column("reserved_until", sa.DateTime, nullable=False),
        sa.Column("order_id", sa.Integer),
        sa.Column("status", sa.String, default="ACTIVE")
    )

    op.create_table(
        "packing_tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, nullable=False),
        sa.Column("sku", sa.String, nullable=False),
        sa.Column("qty", sa.Integer, nullable=False),
        sa.Column("status", sa.String, default="PENDING")
    )


def downgrade():
    for t in [
        "packing_tasks",
        "inventory_reservations",
        "cart_items",
        "carts",
        "customers",
        "product_variants",
        "products",
    ]:
        op.drop_table(t)