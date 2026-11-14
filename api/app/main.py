from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import SessionLocal
from app.database.seed import init_db
from app.routes.archive_routes import router as archive_router
from app.routes.auth_routes import router as auth_router
from app.routes.connection_routes import router as connection_router
from app.routes.alert_routes import router as alert_router
from app.routes.system_routes import router as system_router
from app.routes.analysis_routes import router as analysis_router
from app.routes.sensor_file_problem_routes import router as sensor_file_problem_router
from app.repositories.analysis_repository import AnalysisRepository
from app.ai import engine as ai_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("nids.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Missing, corrupt or incompatible selected artifacts prevent startup.
    ai_engine.configure_detector()
    # Startup: ensure tables exist and seed default admin user
    logger.info("Initializing database tables and admin seed...")
    with SessionLocal() as db:
        init_db(db)
        # Request-driven execution uses one API worker; interrupted requests do not resume silently.
        AnalysisRepository(db).interrupt_running()
        db.commit()
    logger.info("Database initialized successfully.")
    yield
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API & Intelligence Hub for AI Network Intrusion Detection System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware with credentials enabled for HttpOnly cookies
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
prefix = settings.API_PREFIX
app.include_router(archive_router, prefix=prefix)
app.include_router(auth_router, prefix=prefix)
app.include_router(connection_router, prefix=prefix)
app.include_router(alert_router, prefix=prefix)
app.include_router(system_router, prefix=prefix)
app.include_router(analysis_router, prefix=prefix)
app.include_router(sensor_file_problem_router, prefix=prefix)


@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "docs_url": "/docs",
        "health_check": f"{prefix}/system/health",
        "status": "online"
    }
