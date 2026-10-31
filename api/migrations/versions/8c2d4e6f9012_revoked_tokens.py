"""Persist individual JWT logout revocations across API restarts."""
from alembic import op
import sqlalchemy as sa

revision = "8c2d4e6f9012"
down_revision = "7b9c0d1e2f30"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("revoked_tokens"):
        op.create_table("revoked_tokens",
                        sa.Column("fingerprint", sa.String(64), primary_key=True),
                        sa.Column("expires_at", sa.Float(), nullable=False))
        op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade():
    raise RuntimeError("Removing revocations would reactivate logged-out tokens; wait for expiry first.")
