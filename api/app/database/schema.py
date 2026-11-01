from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from app.database.base import Base


def ensure_schema(engine: Engine) -> None:
    api_dir = Path(__file__).resolve().parents[2]
    config = Config(str(api_dir / "alembic.ini"))
    config.set_main_option("script_location", str(api_dir / "migrations"))
    with engine.begin() as connection:
        # Retain the existing empty-database bootstrap, then evolve existing tables.
        Base.metadata.create_all(connection)
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
