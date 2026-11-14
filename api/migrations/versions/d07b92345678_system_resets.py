"""Durable reset exclusion and idempotency; no data is cleared by migration."""
from alembic import op
import sqlalchemy as sa

revision = "d07b92345678"
down_revision = "cf6a81234567"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("system_resets"):
        op.create_table("system_resets", sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index("uq_system_reset_running", "system_resets", ["status"], unique=True,
            sqlite_where=sa.text("status = 'running'"), postgresql_where=sa.text("status = 'running'"))


def downgrade():
    raise RuntimeError("Reset recovery state must be retained; restore a reviewed database backup instead.")
