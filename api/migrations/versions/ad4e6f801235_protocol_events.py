"""Persist UID-linked DNS, HTTP and TLS context independently of connection arrival."""
from alembic import op
import sqlalchemy as sa

revision = "ad4e6f801235"
down_revision = "9d3e5f701234"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("protocol_events"):
        op.create_table("protocol_events", sa.Column("id", sa.String(64), primary_key=True),
                        sa.Column("uid", sa.String(64), nullable=False), sa.Column("log_type", sa.String(8), nullable=False),
                        sa.Column("ts", sa.Float(), nullable=False), sa.Column("fields", sa.JSON(), nullable=False))
        op.create_index("ix_protocol_events_uid_type_ts", "protocol_events", ["uid", "log_type", "ts"])


def downgrade():
    op.drop_table("protocol_events")
