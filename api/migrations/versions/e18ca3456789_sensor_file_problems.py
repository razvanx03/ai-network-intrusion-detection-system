"""Persist blocked archive versions independently of successful read cursors."""
from alembic import op
import sqlalchemy as sa

revision = "e18ca3456789"
down_revision = "d07b92345678"
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table("sensor_file_problems"):
        return
    op.create_table("sensor_file_problems",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("sensor_url", sa.String(512), nullable=False),
        sa.Column("file", sa.String(1024), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("offset", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_session_id", sa.String(32), nullable=False),
        sa.Column("last_session_id", sa.String(32), nullable=False),
        sa.UniqueConstraint("sensor_url", "file", "fingerprint", name="uq_sensor_file_problem_version"))
    op.create_index("ix_sensor_file_problems_scope_status", "sensor_file_problems", ["sensor_url", "status"])


def downgrade():
    raise RuntimeError("Downgrade would remove import-problem history; restore a reviewed backup instead.")
