"""Immutable archive snapshots; legacy batches remain explicitly unavailable."""
from alembic import op
import sqlalchemy as sa

revision = "cf6a81234567"
down_revision = "be5f70912346"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "snapshot_version" not in {c["name"] for c in inspector.get_columns("archive_batches")}:
        op.add_column("archive_batches", sa.Column("snapshot_version", sa.Integer(), nullable=True))
    if "archive_records" not in inspector.get_table_names():
        op.create_table(
            "archive_records",
            sa.Column("batch_id", sa.String(32), sa.ForeignKey("archive_batches.id"), primary_key=True),
            sa.Column("kind", sa.String(24), primary_key=True),
            sa.Column("record_id", sa.String(100), primary_key=True),
            sa.Column("parent_id", sa.String(64), nullable=True),
            sa.Column("member", sa.Boolean(), nullable=False),
            sa.Column("protocol", sa.String(16), nullable=True),
            sa.Column("flagged", sa.Boolean(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
        )
        op.create_index("ix_archive_records_parent", "archive_records", ["batch_id", "kind", "parent_id"])


def downgrade():
    raise RuntimeError("Downgrade would discard historical snapshots; restore a reviewed database backup instead.")
