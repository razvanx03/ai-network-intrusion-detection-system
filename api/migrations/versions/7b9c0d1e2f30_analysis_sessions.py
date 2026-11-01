"""Persist analysis sessions and mark pre-session alerts as legacy demo data."""
from alembic import op
import sqlalchemy as sa

revision = "7b9c0d1e2f30"
down_revision = "eaf7ed8efc1e"
branch_labels = None
depends_on = None


def upgrade():
    # Startup historically uses create_all. Support both bootstrapped and existing DBs.
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("analysis_sessions"):
        op.create_table(
            "analysis_sessions",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("source", sa.String(16), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("detector_status", sa.String(32), nullable=False),
            sa.Column("detector_name", sa.String(64), nullable=False),
            sa.Column("detector_version", sa.String(64)),
            sa.Column("preparation_version", sa.String(64), nullable=False),
            sa.Column("records_received", sa.Integer(), nullable=False),
            sa.Column("new_connections_ingested", sa.Integer(), nullable=False),
            sa.Column("records_prepared", sa.Integer(), nullable=False),
            sa.Column("new_alerts_detected", sa.Integer(), nullable=False),
            sa.Column("error_code", sa.String(32)),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_analysis_sessions_status", "analysis_sessions", ["status"])
        op.create_index("uq_analysis_one_running", "analysis_sessions", ["status"], unique=True,
                        sqlite_where=sa.text("status = 'running'"), postgresql_where=sa.text("status = 'running'"))
    if not sa.inspect(bind).has_table("analysis_session_connections"):
        op.create_table(
            "analysis_session_connections",
            sa.Column("session_id", sa.String(32), sa.ForeignKey("analysis_sessions.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("connection_id", sa.Integer(), sa.ForeignKey("connections.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("sensor_url", sa.String(512)), sa.Column("file_id", sa.String(64)), sa.Column("file", sa.Text()),
        )
    if not sa.inspect(bind).has_table("alert_connections"):
        op.create_table(
            "alert_connections",
            sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("connection_id", sa.Integer(), sa.ForeignKey("connections.id", ondelete="CASCADE"), primary_key=True),
        )
    columns = {column["name"] for column in sa.inspect(bind).get_columns("alerts")}
    if "analysis_session_id" not in columns:
        with op.batch_alter_table("alerts") as batch:
            batch.add_column(sa.Column("analysis_session_id", sa.String(32), nullable=True))
            batch.create_foreign_key("fk_alerts_analysis_session", "analysis_sessions", ["analysis_session_id"], ["id"], ondelete="SET NULL")
            batch.create_index("ix_alerts_analysis_session_id", ["analysis_session_id"])
    if "provenance" not in columns:
        op.add_column("alerts", sa.Column("provenance", sa.String(16), nullable=False, server_default="legacy_demo"))


def downgrade():
    raise RuntimeError("This additive migration preserves analysis history. Restore a database backup to roll back.")
