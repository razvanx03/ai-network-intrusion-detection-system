"""Keep explicit per-file ingestion warnings in analysis history."""
from alembic import op
import sqlalchemy as sa

revision = "9d3e5f701234"
down_revision = "8c2d4e6f9012"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("analysis_sessions")}
    if "file_issues" not in columns:
        op.add_column("analysis_sessions", sa.Column(
            "file_issues", sa.JSON(), nullable=False, server_default=sa.text("'[]'"),
        ))


def downgrade():
    op.drop_column("analysis_sessions", "file_issues")
