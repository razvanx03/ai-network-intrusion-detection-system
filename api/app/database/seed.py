import logging
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_password
from app.database.base import Base
from app.database.session import engine, SessionLocal
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger("nids.seed")


def init_db(db: Session) -> None:
    """Create all tables and seed the initial single admin user if missing."""
    Base.metadata.create_all(bind=engine)

    user_repo = UserRepository(db)
    existing_admin = user_repo.get_by_username(settings.ADMIN_USERNAME)

    if not existing_admin:
        logger.info(f"Seeding default admin user: {settings.ADMIN_USERNAME}")
        hashed_pw = hash_password(settings.ADMIN_PASSWORD)
        user_repo.create(
            username=settings.ADMIN_USERNAME,
            hashed_password=hashed_pw,
            is_admin=True,
        )
        logger.info(f"Admin user '{settings.ADMIN_USERNAME}' created successfully.")
    else:
        logger.info(f"Admin user '{settings.ADMIN_USERNAME}' already exists. Skipping seed.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as session:
        init_db(session)
