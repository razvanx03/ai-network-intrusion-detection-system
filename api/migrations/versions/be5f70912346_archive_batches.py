"""Archive traffic and analysis evidence without deleting data or cursors."""
from alembic import op
import sqlalchemy as sa

revision = "be5f70912346"
down_revision = "ad4e6f801235"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("archive_batches"):
        op.create_table("archive_batches", sa.Column("id", sa.String(32), primary_key=True),
                        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                        sa.Column("restored_at", sa.DateTime(timezone=True)),
                        sa.Column("connections", sa.Integer(), nullable=False),
                        sa.Column("alerts", sa.Integer(), nullable=False),
                        sa.Column("sessions", sa.Integer(), nullable=False))
    for table in ("connections", "alerts", "analysis_sessions"):
        if "archive_batch_id" not in {c["name"] for c in sa.inspect(bind).get_columns(table)}:
            op.add_column(table, sa.Column("archive_batch_id", sa.String(32), nullable=True))
            op.create_index(f"ix_{table}_archive_batch_id", table, ["archive_batch_id"])


def downgrade():
    raise RuntimeError("Archive migration downgrade would discard archival state; restore a reviewed database backup instead.")
